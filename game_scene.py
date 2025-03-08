from Range import *

class GameScene(types.KX_PythonComponent):
    args = []
    
    def start(self, args):
        print("GameScene iniciada!")
        
        # Recuperar player_id e client das variáveis globais
        self.player_id = logic.globalDict.get("player_id")
        self.client = logic.globalDict.get("game_client")
        
        if not self.player_id or not self.client:
            print("Erro: player_id ou client não encontrados!")
            return
            
        print(f"Criando jogador com ID: {self.player_id}")
        
        # Criar jogador na posição inicial
        scene = logic.getCurrentScene()
        spawn_point = scene.objects.get("SpawnPoint")
        if spawn_point:
            pos = spawn_point.worldPosition
        else:
            pos = [0, 0, 0]
            print("Aviso: SpawnPoint não encontrado, usando posição padrão")
        
        # Criar jogador
        jogador = scene.addObject("JogadorTemplate", None, 0)
        jogador.worldPosition = pos
        
        # Configurar componente do jogador
        jogador_comp = jogador.components.get("Jogador")
        if jogador_comp:
            jogador_comp["player_id"] = self.player_id
            print(f"Jogador {self.player_id} criado com sucesso!")
        else:
            print("Erro: Componente Jogador não encontrado!")
    
    def update(self):
        pass
    
    def on_remove(self):
        # Fechar cliente quando a cena for removida
        if self.client:
            self.client.close() 