import asyncio
import websockets
import json
import os
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurações
PORT = int(os.environ.get("PORT", 10000))
HOST = "0.0.0.0"  # Necessário para o Render

# Armazenamento em memória
connected_clients = {}
player_data = {}

async def register_client(websocket, player_id):
    """Registrar novo cliente"""
    connected_clients[player_id] = websocket
    player_data[player_id] = {
        "position": [0, 0, 0],
        "orientation": [0, 0, 0],
        "health": 100,
        "ammo": 100,
        "score": 0,
        "last_update": datetime.now().timestamp()
    }
    logger.info(f"Cliente registrado: {player_id}")
    
    # Notificar outros jogadores
    await broadcast_player_joined(player_id)

async def unregister_client(player_id):
    """Remover cliente"""
    if player_id in connected_clients:
        del connected_clients[player_id]
    if player_id in player_data:
        del player_data[player_id]
    logger.info(f"Cliente removido: {player_id}")
    
    # Notificar outros jogadores
    await broadcast_player_left(player_id)

async def broadcast_player_joined(player_id):
    """Avisar todos que um novo jogador entrou"""
    if player_id in player_data:
        message = {
            "type": "player_joined",
            "data": {
                "player_id": player_id,
                **player_data[player_id]
            }
        }
        await broadcast_message(message, exclude=player_id)

async def broadcast_player_left(player_id):
    """Avisar todos que um jogador saiu"""
    message = {
        "type": "player_left",
        "data": player_id
    }
    await broadcast_message(message)

async def broadcast_message(message, exclude=None):
    """Enviar mensagem para todos os clientes"""
    disconnected = []
    for pid, websocket in connected_clients.items():
        if pid != exclude:
            try:
                await websocket.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected.append(pid)
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem para {pid}: {e}")
                disconnected.append(pid)
    
    # Remover clientes desconectados
    for pid in disconnected:
        await unregister_client(pid)

async def handle_client(websocket):
    """Gerenciar conexão com cliente"""
    player_id = None
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                logger.debug(f"Mensagem recebida: {msg_type}")
                
                # Login ou registro inicial
                if msg_type == "login":
                    player_id = f"player_{datetime.now().timestamp()}"
                    await register_client(websocket, player_id)
                    response = {
                        "type": "login_response",
                        "success": True,
                        "player_id": player_id
                    }
                    await websocket.send(json.dumps(response))
                    continue
                
                # Outros tipos de mensagem precisam de player_id
                if not player_id:
                    continue
                
                # Atualização de posição
                if msg_type == "player_update":
                    if player_id in player_data:
                        player_data[player_id].update(data.get("data", {}))
                        player_data[player_id]["last_update"] = datetime.now().timestamp()
                        await broadcast_message({
                            "type": "player_update",
                            "data": {
                                "player_id": player_id,
                                **data.get("data", {})
                            }
                        }, exclude=player_id)
                
                # Atualização de status
                elif msg_type == "player_status":
                    if player_id in player_data:
                        status_data = data.get("data", {})
                        player_data[player_id].update(status_data)
                        await broadcast_message({
                            "type": "player_status",
                            "data": {
                                "player_id": player_id,
                                **status_data
                            }
                        }, exclude=player_id)
                
                # Tiro disparado
                elif msg_type == "shot":
                    await broadcast_message({
                        "type": "player_shot",
                        "data": {
                            "player_id": player_id,
                            **data.get("data", {})
                        }
                    }, exclude=player_id)
                
                # Jogador atingido
                elif msg_type == "hit":
                    await broadcast_message({
                        "type": "player_hit",
                        "data": {
                            "shooter_id": player_id,
                            **data.get("data", {})
                        }
                    })
                
                # Requisição de lista de jogadores
                elif msg_type == "request_player_list":
                    # Enviar dados de todos os jogadores ativos
                    for pid, pdata in player_data.items():
                        if pid != player_id:
                            await websocket.send(json.dumps({
                                "type": "player_joined",
                                "data": {
                                    "player_id": pid,
                                    **pdata
                                }
                            }))
                
            except json.JSONDecodeError:
                logger.error(f"Mensagem inválida recebida de {player_id}")
            except Exception as e:
                logger.error(f"Erro ao processar mensagem: {e}")
                
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Cliente desconectado: {player_id}")
    except Exception as e:
        logger.error(f"Erro na conexão: {e}")
    finally:
        if player_id:
            await unregister_client(player_id)

async def cleanup_inactive_players():
    """Remover jogadores inativos"""
    while True:
        try:
            now = datetime.now().timestamp()
            inactive = []
            for pid, data in player_data.items():
                if now - data["last_update"] > 30:  # 30 segundos sem atualização
                    inactive.append(pid)
            
            for pid in inactive:
                await unregister_client(pid)
            
            await asyncio.sleep(10)  # Verificar a cada 10 segundos
        except Exception as e:
            logger.error(f"Erro na limpeza de jogadores inativos: {e}")
            await asyncio.sleep(10)

async def health_check():
    """Endpoint para verificação de saúde do servidor"""
    while True:
        try:
            logger.info(f"Servidor ativo. Clientes conectados: {len(connected_clients)}")
            await asyncio.sleep(30)  # Log a cada 30 segundos
        except Exception as e:
            logger.error(f"Erro no health check: {e}")
            await asyncio.sleep(30)

async def main():
    """Função principal do servidor"""
    try:
        logger.info(f"Iniciando servidor WebSocket em {HOST}:{PORT}")
        
        # Iniciar tarefas de manutenção
        asyncio.create_task(cleanup_inactive_players())
        asyncio.create_task(health_check())
        
        # Iniciar servidor WebSocket
        async with websockets.serve(handle_client, HOST, PORT):
            logger.info("Servidor WebSocket iniciado com sucesso!")
            await asyncio.Future()  # Rodar indefinidamente
            
    except Exception as e:
        logger.error(f"Erro fatal no servidor: {e}")
        raise  # Re-raise para o Render ver o erro

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Servidor encerrado pelo usuário")
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        raise  # Re-raise para o Render ver o erro 