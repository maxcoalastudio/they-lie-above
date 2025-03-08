import websocket
import json
import threading
import time
import uuid
import os

class GameClient:
    def __init__(self):
        self.ws = None
        self.callbacks = {}
        self.connected = False
        self.should_run = True
        self.player_id = None
        self.reconnect_delay = 1.0
        self.max_reconnect_delay = 30.0
        self.timeout = 15  # Aumentado para 15 segundos
        self.login_response = None
        self.server_url = "wss://they-lie-above.onrender.com/ws"  # URL do servidor no Render com path /ws
        self.offline_mode = True  # Começar em modo offline
        self.players_data = {}  # Dados dos jogadores
        self.local_data_file = "player_data.json"
        
        # Carregar dados locais
        self.load_local_data()
        
        # Iniciar conexão
        self.connect()
    
    def load_local_data(self):
        """Carregar dados salvos localmente"""
        try:
            if os.path.exists(self.local_data_file):
                with open(self.local_data_file, 'r') as f:
                    self.players_data = json.load(f)
        except:
            self.players_data = {}
    
    def save_local_data(self):
        """Salvar dados localmente"""
        try:
            with open(self.local_data_file, 'w') as f:
                json.dump(self.players_data, f)
        except:
            print("Erro ao salvar dados locais")
    
    def connect(self):
        """Conectar ao servidor"""
        try:
            websocket.enableTrace(True)  # Ativar debug
            self.ws = websocket.WebSocketApp(
                self.server_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Iniciar thread do WebSocket
            self.thread = threading.Thread(target=self._run_websocket)
            self.thread.daemon = True
            self.thread.start()
            
            # Esperar conexão inicial
            start_time = time.time()
            while not self.connected and time.time() - start_time < 10:  # 10 segundos para conectar
                time.sleep(0.1)
                
            if not self.connected:
                print("Timeout ao conectar ao servidor")
                
        except Exception as e:
            print(f"Erro ao conectar: {e}")
    
    def _run_websocket(self):
        """Executar WebSocket em loop com reconexão"""
        while self.should_run:
            try:
                self.ws.run_forever()
                if self.should_run:
                    print("Conexão perdida. Tentando reconectar...")
                    time.sleep(self.reconnect_delay)
                    self.reconnect_delay = min(self.reconnect_delay * 1.5, self.max_reconnect_delay)
                    self.connect()
            except Exception as e:
                print(f"Erro no WebSocket: {e}")
                time.sleep(self.reconnect_delay)
    
    def _on_open(self, ws):
        """Callback quando conexão é estabelecida"""
        print("Conexão WebSocket estabelecida")
        self.connected = True
        self.reconnect_delay = 1.0  # Reset do delay de reconexão
        self.offline_mode = False
        
        # Sincronizar dados offline
        if self.player_id:
            self.sync_offline_data()
    
    def _on_message(self, ws, message):
        """Callback quando mensagem é recebida"""
        try:
            data = json.loads(message)
            event_type = data.get("type")
            
            if event_type == "login_response":
                print(f"Resposta de login recebida: {data}")
                self.login_response = data
                if data.get("success"):
                    self.player_id = data.get("player_id")
                    self.players_data[self.player_id] = {
                        "email": data.get("email"),
                        "last_login": time.time()
                    }
                    self.save_local_data()
            
            if event_type in self.callbacks:
                self.callbacks[event_type](data)
        except Exception as e:
            print(f"Erro ao processar mensagem: {e}")
    
    def _on_error(self, ws, error):
        """Callback quando ocorre erro"""
        print(f"Erro WebSocket: {error}")
        self.offline_mode = True
        self.connected = False
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Callback quando conexão é fechada"""
        print(f"Conexão WebSocket fechada: {close_status_code} - {close_msg}")
        self.offline_mode = True
        self.connected = False
    
    def login(self, email, password):
        """Login no servidor"""
        if not self.connected:
            return {"success": False, "error": "Não conectado ao servidor"}
        
        try:
            # Resetar resposta de login anterior
            self.login_response = None
            
            # Enviar requisição de login
            login_data = {
                "type": "login",
                "email": email,
                "password": password
            }
            
            print("Enviando requisição de login...")
            if not self.send_message(login_data):
                return {"success": False, "error": "Falha ao enviar login"}
            
            # Esperar resposta
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                if self.login_response:
                    response = self.login_response
                    self.login_response = None
                    return {
                        "success": response.get("success", False),
                        "player_id": response.get("player_id"),
                        "error": response.get("error")
                    }
                time.sleep(0.1)
            
            return {"success": False, "error": "Timeout esperando resposta do servidor"}
            
        except Exception as e:
            print(f"Erro no login: {e}")
            return {"success": False, "error": str(e)}
    
    def sync_offline_data(self):
        """Sincronizar dados offline com servidor"""
        if not self.connected or not self.player_id:
            return
            
        try:
            self.send_message({
                "type": "sync",
                "player_id": self.player_id,
                "data": self.players_data.get(self.player_id, {})
            })
        except:
            pass
    
    def send_message(self, message):
        """Enviar mensagem com retry"""
        if not self.connected:
            print("Não conectado ao servidor")
            return False
            
        try:
            print(f"Enviando mensagem: {message}")
            self.ws.send(json.dumps(message))
            return True
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")
            self.connected = False
            self.offline_mode = True
            return False
    
    def update_position(self, player_id, position, rotation):
        """Atualizar posição do jogador"""
        if not self.connected:
            return
        
        self.players_data[player_id]["position"] = position
        self.players_data[player_id]["rotation"] = rotation
        self.players_data[player_id]["last_update"] = time.time()
        
        self.send_message({
            "type": "position",
            "player_id": player_id,
            "position": position,
            "rotation": rotation
        })
    
    def send_shot(self, player_id, position, direction):
        """Enviar informação de tiro"""
        if not self.connected:
            return
        
        self.send_message({
            "type": "shot",
            "player_id": player_id,
            "position": position,
            "direction": direction
        })
    
    def get_other_players(self):
        """Obter outros jogadores"""
        current_time = time.time()
        active_players = {}
        
        for pid, data in self.players_data.items():
            if pid != self.player_id:
                if current_time - data.get("last_update", 0) < 30:  # 30 segundos timeout
                    active_players[pid] = data
        
        return active_players
    
    def on(self, event_type, callback):
        """Registrar callback para tipo de evento"""
        self.callbacks[event_type] = callback
    
    def close(self):
        """Fechar conexão e salvar dados"""
        self.should_run = False
        if self.ws:
            self.ws.close()
        self.save_local_data()
        self.connected = False 