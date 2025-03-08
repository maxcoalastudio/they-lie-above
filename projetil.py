from Range import *
from mathutils import Vector
import time

SPAWN_POINTS = [
    Vector((0, 0, 0)),    # Posição inicial jogador 1
    Vector((10, 0, 0)),   # Posição inicial jogador 2
]

class Projetil(types.KX_PythonComponent):
    args = [
        ("velocidade", 50.0),
        ("dano", 25.0),
        ("tempo_vida", 3.0),
        ("delay_colisao", 0.1)  # Tempo em segundos antes de ativar colisão
    ]

    def start(self, args):
        # Configurar valores dos argumentos
        for key, value in self.args:
            setattr(self, key, args.get(key, value))
        
        # Inicializar variáveis
        self.tempo_criacao = time.time()
        self.jogador_origem = None  # Será definido pelo jogador que atirou
        self.colisao_ativa = False
        
        # Mover o projétil um pouco para frente do avião
        self.object.applyMovement([0, 2.0, 0], True)
        
        print("Projétil criado!")
        
    def verificar_colisao(self):
        # Verificar se há colisão usando o sensor
        collision = self.object.sensors.get('Collision')
        if collision and collision.positive:
            objeto_atingido = collision.hitObject
            
            # Ignorar colisão com o próprio atirador
            if objeto_atingido == self.jogador_origem:
                return
                
            # Verificar se atingiu outro jogador
            if "Jogador" in objeto_atingido.name:
                # Pegar o componente do jogador atingido
                jogador_comp = objeto_atingido.components.get("Jogador")
                if jogador_comp:
                    # Aplicar dano
                    jogador_comp.take_damage(self.dano)
                    print(f"Jogador {self.jogador_origem.name} acertou {objeto_atingido.name} - Dano: {self.dano}")
                    
                    # Atualizar score do atirador se acertou
                    if self.jogador_origem and hasattr(self.jogador_origem, "components"):
                        atirador_comp = self.jogador_origem.components.get("Jogador")
                        if atirador_comp:
                            atirador_comp.add_score(10)  # 10 pontos por acerto
            
            # Destruir o projétil ao colidir
            self.object.endObject()
            print("Projétil destruído por colisão!")
        
    def update(self):
        tempo_atual = time.time()
        
        # Verificar tempo de vida
        if tempo_atual - self.tempo_criacao > self.tempo_vida:
            self.object.endObject()
            print("Projétil destruído por tempo de vida!")
            return
            
        # Verificar colisões após o delay
        if not self.colisao_ativa and (tempo_atual - self.tempo_criacao) > self.delay_colisao:
            self.colisao_ativa = True
            
        if self.colisao_ativa:
            self.verificar_colisao()
            
        # Mover o projétil para frente
        self.object.applyMovement([0, self.velocidade * 0.05, 0], True) 