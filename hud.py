import bge
from mathutils import Vector
import math

class HUD(types.KX_PythonComponent):
    args = {
        'radar_size': 200,
        'radar_range': 1000,
        'radar_position': Vector([100, 100]),
    }

    def start(self, args):
        self.radar_size = args['radar_size']
        self.radar_range = args['radar_range']
        self.radar_position = args['radar_position']
        
        # Configurar overlay do radar
        self.overlay = bge.render.getOverlay()
        
    def world_to_radar(self, world_pos, player_pos, player_rot):
        # Converter posição do mundo para coordenadas do radar
        diff = world_pos - player_pos
        
        # Rotacionar baseado na orientação do jogador
        angle = math.atan2(diff.y, diff.x) - player_rot.z
        distance = diff.length
        
        # Normalizar distância para o tamanho do radar
        radar_distance = (distance / self.radar_range) * (self.radar_size / 2)
        
        # Converter para coordenadas polares
        x = self.radar_position.x + radar_distance * math.cos(angle)
        y = self.radar_position.y + radar_distance * math.sin(angle)
        
        return Vector([x, y])
    
    def update(self):
        # Limpar radar
        self.overlay.clear()
        
        # Desenhar borda do radar
        self.draw_radar_border()
        
        # Obter posição e rotação do jogador
        player = self.object
        player_pos = player.worldPosition
        player_rot = player.worldOrientation.to_euler()
        
        # Desenhar outros jogadores no radar
        scene = bge.logic.getCurrentScene()
        for obj in scene.objects:
            if obj.name.startswith("Player") and obj != player:
                radar_pos = self.world_to_radar(obj.worldPosition, player_pos, player_rot)
                self.draw_blip(radar_pos, "enemy")
        
        # Desenhar HUD
        self.draw_hud_info()
    
    def draw_radar_border(self):
        self.overlay.drawLine(
            int(self.radar_position.x - self.radar_size/2),
            int(self.radar_position.y - self.radar_size/2),
            int(self.radar_position.x + self.radar_size/2),
            int(self.radar_position.y + self.radar_size/2),
            [1, 1, 1, 0.5]
        )
    
    def draw_blip(self, position, type):
        color = [1, 0, 0, 1] if type == "enemy" else [0, 1, 0, 1]
        self.overlay.drawLine(
            int(position.x - 2),
            int(position.y - 2),
            int(position.x + 2),
            int(position.y + 2),
            color
        )
    
    def draw_hud_info(self):
        player = self.object
        
        # Desenhar informações do jogador
        health_text = f"Vida: {player['health']:.0f}"
        ammo_text = f"Munição: {player['ammo']}"
        fuel_text = f"Combustível: {player['fuel']:.0f}"
        
        self.overlay.drawText(health_text, 10, 10, [1, 1, 1, 1])
        self.overlay.drawText(ammo_text, 10, 30, [1, 1, 1, 1])
        self.overlay.drawText(fuel_text, 10, 50, [1, 1, 1, 1]) 