from Range import *
from collections import OrderedDict
from mathutils import Vector, Matrix
import time
from websocket_client import GameClient


class Jogador(types.KX_PythonComponent):
    args = [
        ("speed", 0.03),
        ("rotation_speed", 0.005),
        ("fuel", 100.0),
        ("fuel_consumption_rate", 0.1),
        ("collision_threshold", 10.0),
        ("health", 100.0),
        ("max_health", 100.0),
        ("ammo", 100),
        ("max_ammo", 100),
        ("shoot_delay", 0.2),
        ("dano_colisao", 50.0),
        ("pontos_abate", 100),
        ("tempo_respawn", 5.0),
        ("player_id", "")  # ID único para cada jogador
    ]

    def start(self, args):
        # Inicializar variáveis de controle
        self.ligando = False
        self.is_dead = False
        self.last_shot_time = 0
        self.score = 0
        self.kills = 0
        self.deaths = 0
        self.respawn_time = 0
        self.last_key_state = False
        self.last_sync_time = 0
        self.sync_interval = 0.1  # Sincronizar a cada 100ms
        
        # Configurar valores dos argumentos
        for key, value in self.args:
            setattr(self, key, args.get(key, value))
        
        # Inicializar cliente WebSocket
        self.client = GameClient()
        
        # Registrar callbacks para eventos
        self.client.on("player_update", self.on_player_update)
        self.client.on("player_shot", self.on_player_shot)
        self.client.on("player_hit", self.on_player_hit)
        self.client.on("player_spawn", self.on_player_spawn)
        self.client.on("player_die", self.on_player_die)
        
        # Configurar física
        self.object.setDamping(0.5, 0.5)
        self.object.setLinearVelocity([0, 0, 0])
        self.object.setAngularVelocity([0, 0, 0])
        
        # Salvar posição inicial para respawn
        self.spawn_position = self.object.worldPosition.copy()
        self.spawn_orientation = self.object.worldOrientation.copy()
        
        print(f"Jogador {self.player_id} inicializado!")
        print(f"Vida: {self.health}")
        print(f"Munição: {self.ammo}")

    def on_player_update(self, data):
        """Callback quando outro jogador atualiza sua posição"""
        if data["player_id"] != self.player_id:
            # Atualizar ou criar outro jogador
            outro_jogador = logic.getCurrentScene().objects.get(f"Jogador_{data['player_id']}")
            if not outro_jogador:
                outro_jogador = logic.getCurrentScene().addObject("JogadorTemplate", self.object)
                outro_jogador.name = f"Jogador_{data['player_id']}"
            
            # Atualizar posição e rotação
            pos = data["position"]
            rot = data["rotation"]
            outro_jogador.worldPosition = Vector((pos[0], pos[1], pos[2]))
            outro_jogador.worldOrientation = Matrix.Rotation(rot[2], 3, 'Z') @ Matrix.Rotation(rot[1], 3, 'Y') @ Matrix.Rotation(rot[0], 3, 'X')

    def on_player_shot(self, data):
        """Callback quando outro jogador atira"""
        if data["player_id"] != self.player_id:
            # Criar projétil na posição do outro jogador
            outro_jogador = logic.getCurrentScene().objects.get(f"Jogador_{data['player_id']}")
            if outro_jogador:
                pos = data["position"]
                dir = data["direction"]
                bullet = logic.getCurrentScene().addObject("BulletTemplate", outro_jogador)
                bullet.worldPosition = Vector((pos[0], pos[1], pos[2]))
                bullet.setLinearVelocity([dir[0] * 50, dir[1] * 50, dir[2] * 50])

    def on_player_hit(self, data):
        """Callback quando este jogador é atingido"""
        if data["target_id"] == self.player_id:
            self.take_damage(data["damage"], data["shooter_id"])

    def on_player_spawn(self, data):
        """Callback quando outro jogador spawna"""
        if data["player_id"] != self.player_id:
            outro_jogador = logic.getCurrentScene().objects.get(f"Jogador_{data['player_id']}")
            if outro_jogador:
                pos = data["position"]
                rot = data["rotation"]
                outro_jogador.worldPosition = Vector((pos[0], pos[1], pos[2]))
                outro_jogador.worldOrientation = Matrix.Rotation(rot[2], 3, 'Z') @ Matrix.Rotation(rot[1], 3, 'Y') @ Matrix.Rotation(rot[0], 3, 'X')
                logic.getCurrentScene().addObject("RespawnEffect", outro_jogador)

    def on_player_die(self, data):
        """Callback quando outro jogador morre"""
        if data["player_id"] != self.player_id:
            outro_jogador = logic.getCurrentScene().objects.get(f"Jogador_{data['player_id']}")
            if outro_jogador:
                logic.getCurrentScene().addObject("ExplosionEffect", outro_jogador)

    def sync_position(self):
        """Sincronizar posição com o servidor"""
        if time.time() - self.last_sync_time > self.sync_interval:
            pos = self.object.worldPosition
            rot = self.object.worldOrientation.to_euler()
            self.client.update_position(
                self.player_id,
                [pos.x, pos.y, pos.z],
                [rot.x, rot.y, rot.z]
            )
            self.last_sync_time = time.time()

    def shoot(self):
        if self.is_dead:
            return
            
        if self.ammo > 0 and time.time() - self.last_shot_time > self.shoot_delay:
            # Calcular posição inicial do projétil
            direcao = self.object.getAxisVect([0, 1, 0])
            posicao_tiro = self.object.worldPosition + direcao * 2.0
            
            # Criar projétil
            bullet = logic.getCurrentScene().addObject("BulletTemplate", self.object)
            bullet.worldPosition = posicao_tiro
            bullet.worldOrientation = self.object.worldOrientation
            
            # Configurar projétil
            bullet_comp = bullet.components.get("Projetil")
            if bullet_comp:
                bullet_comp.jogador_origem = self.object
                print("Projétil configurado com sucesso!")
            else:
                print("ERRO: Componente Projetil não encontrado!")
                bullet.endObject()
                return
            
            # Aplicar velocidade e notificar servidor
            bullet.setLinearVelocity(direcao * 50.0)
            self.client.send_shot(self.player_id, [posicao_tiro.x, posicao_tiro.y, posicao_tiro.z], [direcao.x, direcao.y, direcao.z])
            
            self.ammo -= 1
            self.last_shot_time = time.time()
            print(f"Tiro disparado! Munição restante: {self.ammo}")

    def update(self):
        if not self.is_dead:
            self.direcaoPlane()
            self.sync_position()
            
            # Verificar tecla de tiro
            keyboard = logic.keyboard.inputs
            if keyboard[events.SPACEKEY].active and not self.last_key_state:
                self.shoot()
            self.last_key_state = keyboard[events.SPACEKEY].active
        elif time.time() > self.respawn_time:
            self.respawn()
            
    def on_remove(self):
        if hasattr(self, 'client') and self.client:
            self.client.close()

    def direcaoPlane(self):
        keyboard = logic.keyboard.inputs
        
        if not self.ligando:
            def trigger1Collision(objeto):
                if "obj" in objeto:
                    print(objeto)
                    if keyboard[events.SPACEKEY].active:
                        self.object.applyMovement([0, self.speed/4, 0], True)
                        self.ligando = True
                    return True
            self.object.collisionCallbacks.append(trigger1Collision)
            print('ligado')
        else:        
            if self.fuel > 0:
                if keyboard[events.WKEY].active:
                    self.object.applyMovement([0, self.speed*1.5, 0.04], True)
                    self.fuel -= 0.00001
                else:
                    # Aceleração gradual sem while loop
                    self.object.applyMovement([0, self.speed, 0.04], True)
                    self.fuel -= 0.00005
                    
        if self.ligando:
            keyboard = logic.keyboard.inputs
            if keyboard[events.UPARROWKEY].active:
                self.object.applyRotation([-self.rotation_speed, 0, 0], True)
            if keyboard[events.DOWNARROWKEY].active:
                self.object.applyRotation([self.rotation_speed, 0, 0], True)
            if keyboard[events.LEFTARROWKEY].active:
                self.object.applyRotation([0, -self.rotation_speed, 0], True)
            if keyboard[events.RIGHTARROWKEY].active:
                self.object.applyRotation([0, self.rotation_speed, 0], True)
            if keyboard[events.AKEY].active:
                self.object.applyRotation([0, 0, self.rotation_speed/5], True)
            if keyboard[events.DKEY].active:
                self.object.applyRotation([0, 0, -self.rotation_speed/5], True)
                
    def take_damage(self, amount, attacker_id=None):
        if self.is_dead:
            return
            
        self.health -= amount
        print(f"Vida restante: {self.health}")
        
        if self.health <= 0:
            if attacker_id:
                # Atualizar estatísticas do atacante
                attacker_data = self.client.get_player_data(attacker_id)
                if attacker_data:
                    self.client.update_player_stats(
                        attacker_id,
                        kills=attacker_data['stats'].get('kills', 0) + 1,
                        score=attacker_data['stats'].get('score', 0) + self.pontos_abate
                    )
            self.die()
    
    def die(self):
        if not self.is_dead:
            self.is_dead = True
            self.deaths += 1
            self.respawn_time = time.time() + self.tempo_respawn
            print("Jogador morreu!")
            
            # Desativar física e colisões
            self.object.suspendDynamics()
            
            # Efeito de explosão
            logic.getCurrentScene().addObject("ExplosionEffect", self.object)
    
    def respawn(self):
        self.is_dead = False
        self.health = self.max_health
        self.ammo = self.max_ammo
        print("Jogador renasceu!")
        
        # Restaurar posição inicial
        self.object.worldPosition = self.spawn_position.copy()
        self.object.worldOrientation = self.spawn_orientation.copy()
        
        # Reativar física
        self.object.restoreDynamics()
        self.object.setLinearVelocity([0, 0, 0])
        self.object.setAngularVelocity([0, 0, 0])
        
        # Efeito de respawn
        logic.getCurrentScene().addObject("RespawnEffect", self.object)
    
    def add_score(self, points):
        self.score += points
        self.client.update_player_stats(
            self.player_id,
            kills=self.kills,
            deaths=self.deaths,
            score=self.score
        )
        print(f"Pontuação: {self.score}")
    
    def add_kill(self):
        self.kills += 1
        self.add_score(self.pontos_abate)
        print(f"Abates: {self.kills}")
    
            
        