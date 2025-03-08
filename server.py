import asyncio
import websockets
import json
import sqlite3
import bcrypt
import time
from datetime import datetime
from typing import Dict
import logging
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
PORT = int(os.getenv('PORT', 10000))
HOST = '0.0.0.0'  # Necessário para o Render
DATABASE_URL = os.getenv('DATABASE_URL', 'game.db')
WEBSOCKET_MAX_SIZE = int(os.getenv('WEBSOCKET_MAX_SIZE', 10485760))  # 10MB default
MAX_CONNECTIONS = int(os.getenv('MAX_CONNECTIONS', 1000))
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Gerenciador de conexões
class GameServer:
    def __init__(self):
        self.players = {}  # {websocket: player_data}
        self.connections = {}  # {player_id: websocket}
        self.connection_count = 0
        self.init_db()
        logging.info("Servidor inicializado")
    
    def init_db(self):
        """Inicializar banco de dados"""
        try:
            conn = sqlite3.connect(DATABASE_URL)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE,
                    password TEXT,
                    stats TEXT
                )
            ''')
            conn.commit()
            conn.close()
            logging.info("Banco de dados inicializado")
        except Exception as e:
            logging.error(f"Erro ao inicializar banco de dados: {e}")
            raise
    
    def db_operation(self, operation):
        """Executar operação no banco de dados de forma segura"""
        try:
            conn = sqlite3.connect(DATABASE_URL)
            result = operation(conn)
            conn.close()
            return result
        except Exception as e:
            logging.error(f"Erro na operação do banco: {e}")
            raise
    
    async def register(self, websocket, data):
        """Registrar novo jogador"""
        email = data.get('email')
        password = data.get('password')
        
        logging.info(f"Tentativa de registro: {email}")
        
        try:
            def register_op(conn):
                c = conn.cursor()
                player_id = f"player_{int(time.time()*1000)}"
                
                c.execute(
                    'INSERT INTO players (id, email, password, stats) VALUES (?, ?, ?, ?)',
                    (player_id, email, password, json.dumps({
                        "score": 0,
                        "kills": 0,
                        "deaths": 0
                    }))
                )
                conn.commit()
                return player_id
                
            player_id = self.db_operation(register_op)
            
            # Adicionar jogador à lista de conectados
            self.players[websocket] = {
                'id': player_id,
                'email': email,
                'position': [0, 0, 0],
                'rotation': [0, 0, 0],
                'last_update': time.time()
            }
            
            # Registrar conexão
            self.connections[player_id] = websocket
            
            response = {
                'type': 'login_response',
                'success': True,
                'player_id': player_id,
                'email': email
            }
            
            await websocket.send(json.dumps(response))
            logging.info(f"Registro bem sucedido: {email} (ID: {player_id})")
            
            # Notificar outros jogadores
            await self.broadcast_player_joined(player_id)
            
        except Exception as e:
            error_msg = f"Erro no registro: {str(e)}"
            logging.error(error_msg)
            await websocket.send(json.dumps({
                'type': 'login_response',
                'success': False,
                'error': error_msg
            }))
    
    async def login(self, websocket, data):
        """Login de jogador"""
        email = data.get('email')
        password = data.get('password')
        
        logging.info(f"Tentativa de login: {email}")
        
        try:
            def login_op(conn):
                c = conn.cursor()
                c.execute('SELECT id, password FROM players WHERE email = ?', (email,))
                return c.fetchone()
                
            result = self.db_operation(login_op)
            
            if not result:
                logging.info(f"Usuário não encontrado, tentando registrar: {email}")
                await self.register(websocket, data)
                return
                
            player_id, stored_password = result
            
            if password == stored_password:
                # Adicionar jogador à lista de conectados
                self.players[websocket] = {
                    'id': player_id,
                    'email': email,
                    'position': [0, 0, 0],
                    'rotation': [0, 0, 0],
                    'last_update': time.time()
                }
                
                # Registrar conexão
                self.connections[player_id] = websocket
                
                response = {
                    'type': 'login_response',
                    'success': True,
                    'player_id': player_id,
                    'email': email
                }
                
                await websocket.send(json.dumps(response))
                logging.info(f"Login bem sucedido: {email} (ID: {player_id})")
                
                # Notificar outros jogadores
                await self.broadcast_player_joined(player_id)
                
            else:
                error_msg = "Senha incorreta"
                logging.warning(f"Tentativa de login com senha incorreta: {email}")
                await websocket.send(json.dumps({
                    'type': 'login_response',
                    'success': False,
                    'error': error_msg
                }))
                
        except Exception as e:
            error_msg = f"Erro no login: {str(e)}"
            logging.error(error_msg)
            await websocket.send(json.dumps({
                'type': 'login_response',
                'success': False,
                'error': error_msg
            }))
    
    async def update_position(self, websocket, data):
        """Atualizar posição do jogador"""
        if websocket not in self.players:
            return
            
        player = self.players[websocket]
        player['position'] = data.get('position', [0, 0, 0])
        player['rotation'] = data.get('rotation', [0, 0, 0])
        player['last_update'] = time.time()
        
        # Enviar atualização para outros jogadores
        await self.broadcast_position(player['id'], player['position'], player['rotation'])
        
    async def handle_shot(self, websocket, data):
        """Processar tiro do jogador"""
        if websocket not in self.players:
            return
            
        player = self.players[websocket]
        
        # Enviar informação do tiro para outros jogadores
        await self.broadcast_shot(player['id'], player['position'], player['rotation'])
        
    async def handle_damage(self, websocket, data):
        """Processar dano causado"""
        if websocket not in self.players:
            return
            
        player = self.players[websocket]
        target_id = data.get('target_id')
        amount = data.get('amount', 0)
        
        # Enviar dano para o jogador alvo
        await self.broadcast_damage(target_id, amount, player['id'])
        
    async def broadcast_player_joined(self, player_id):
        """Notificar todos sobre novo jogador"""
        message = {
            'type': 'player_joined',
            'player_id': player_id,
            'data': self.players[player_id]
        }
        await self.broadcast(message, exclude=player_id)
        
    async def broadcast_position(self, player_id, position, rotation):
        """Enviar posição do jogador para todos"""
        message = {
            'type': 'position_update',
            'player_id': player_id,
            'position': position,
            'rotation': rotation
        }
        await self.broadcast(message, exclude=player_id)
        
    async def broadcast_shot(self, player_id, position, direction):
        """Enviar informação de tiro para todos"""
        message = {
            'type': 'shot_fired',
            'player_id': player_id,
            'position': position,
            'direction': direction
        }
        await self.broadcast(message, exclude=player_id)
        
    async def broadcast_damage(self, target_id, amount, attacker_id):
        """Enviar informação de dano para o alvo"""
        message = json.dumps({
            'type': 'take_damage',
            'target_id': target_id,
            'amount': amount,
            'attacker_id': attacker_id
        })
        await self.broadcast(message)
        
    async def broadcast(self, message, exclude=None):
        """Enviar mensagem para todos os jogadores exceto o especificado"""
        for pid, websocket in self.connections.items():
            if pid != exclude:
                try:
                    await websocket.send(json.dumps(message))
                except:
                    pass
                
    async def remove_player(self, websocket):
        """Remover jogador quando desconectar"""
        if websocket in self.players:
            player_id = self.players[websocket]['id']
            del self.players[websocket]
            
            # Notificar outros sobre a desconexão
            message = json.dumps({
                'type': 'player_left',
                'player_id': player_id
            })
            await self.broadcast(message)
            
    async def handle_connection(self, websocket, path):
        """Gerenciar conexão com cliente"""
        client_id = id(websocket)
        logging.info(f"Nova conexão: {client_id}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type', '')
                    logging.debug(f"Mensagem recebida de {client_id}: {message_type}")
                    
                    if message_type == 'login':
                        await self.login(websocket, data)
                    elif message_type == 'position':
                        await self.update_position(websocket, data)
                    elif message_type == 'shot':
                        await self.handle_shot(websocket, data)
                    elif message_type == 'damage':
                        await self.handle_damage(websocket, data)
                    else:
                        logging.warning(f"Tipo de mensagem desconhecido: {message_type}")
                        
                except json.JSONDecodeError:
                    logging.error(f"Mensagem inválida recebida de {client_id}")
                except Exception as e:
                    logging.error(f"Erro ao processar mensagem de {client_id}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logging.info(f"Conexão fechada: {client_id}")
        finally:
            await self.remove_player(websocket)
            logging.info(f"Cliente removido: {client_id}")

async def main():
    server = GameServer()
    print(f"Iniciando servidor em {HOST}:{PORT}")
    async with websockets.serve(
        server.handle_connection, 
        HOST, 
        PORT,
        max_size=WEBSOCKET_MAX_SIZE,
        max_queue=MAX_CONNECTIONS
    ):
        await asyncio.Future()  # Executar indefinidamente

if __name__ == "__main__":
    asyncio.run(main()) 