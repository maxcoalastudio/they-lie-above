import sys
print("Python path:", sys.executable)

from Range import *
from websocket_client import GameClient

class LoginScene(types.KX_PythonComponent):
    args = []

    def start(self, args):
        print("LoginScene iniciada!")
        self.email = ""
        self.password = ""
        self.is_typing_email = True
        self.show_error = False
        self.error_message = ""
        self.logged_in = False
        
        # Inicializar cliente WebSocket
        self.client = GameClient()
        
        # Obter referências aos objetos de texto
        scene = logic.getCurrentScene()
        self.title_text = scene.objects.get("TitleText")
        self.email_text = scene.objects.get("EmailText")
        self.password_text = scene.objects.get("PasswordText")
        self.instructions_text = scene.objects.get("InstructionsText")
        self.error_text = scene.objects.get("ErrorText")
        
        if self.error_text:
            self.error_text.visible = False
        
        # Atualizar textos iniciais
        if self.email_text:
            self.email_text.text = "Email: "
        if self.password_text:
            self.password_text.text = "Senha: "
        if self.instructions_text:
            self.instructions_text.text = "TAB: Alternar campos | ENTER: Login"
    
    def update_display(self):
        if self.email_text:
            self.email_text.text = "Email: " + self.email + ("_" if self.is_typing_email else "")
        
        if self.password_text:
            self.password_text.text = "Senha: " + "*" * len(self.password) + ("_" if not self.is_typing_email else "")
        
        if self.error_text:
            self.error_text.visible = self.show_error
            if self.show_error:
                self.error_text.text = self.error_message
    
    def handle_input(self):
        keyboard = logic.keyboard.inputs
        
        # Alternar entre campos com TAB
        if keyboard[events.TABKEY].activated:
            self.is_typing_email = not self.is_typing_email
            return
            
        # Processar teclas
        for key, status in keyboard.items():
            if status.activated:
                if key == events.ENTERKEY:
                    self.try_login()
                elif key == events.BACKSPACEKEY:
                    if self.is_typing_email:
                        self.email = self.email[:-1]
                    else:
                        self.password = self.password[:-1]
                # Letras
                elif events.AKEY <= key <= events.ZKEY:
                    char = chr(key - events.AKEY + ord('a'))
                    if self.is_typing_email:
                        self.email += char
                    else:
                        self.password += char
                # Números
                elif events.ZEROKEY <= key <= events.NINEKEY:
                    char = chr(key - events.ZEROKEY + ord('0'))
                    if self.is_typing_email:
                        self.email += char
                    else:
                        self.password += char
                # Caracteres especiais para email
                elif key == events.PERIODKEY:  # Ponto
                    if self.is_typing_email:
                        self.email += "."
                elif key == events.MINUSKEY:  # Hífen
                    if self.is_typing_email:
                        self.email += "-"
                elif key == events.ACCENTGRAVEKEY:  # @ (usando a tecla ´)
                    if self.is_typing_email:
                        self.email += "@"
    
    def try_login(self):
        print("Tentando fazer login...")
        if not self.email or not self.password:
            self.show_error = True
            self.error_message = "Preencha todos os campos!"
            return
        
        print(f"Email: {self.email}, Senha: {self.password}")
        
        try:
            # Login (funciona offline e online)
            response = self.client.login(self.email, self.password)
            
            if response["success"]:
                print("Login bem sucedido!")
                
                # Armazenar dados nas variáveis globais
                logic.globalDict["player_id"] = response["player_id"]
                logic.globalDict["game_client"] = self.client
                
                # Mudar para a cena do jogo
                print("Mudando para a cena do jogo...")
                self.logged_in = True
                
                # Carregar cena do jogo
                scene = logic.getCurrentScene()
                scene.replace("GameScene")
                print("Cena do jogo carregada!")
            else:
                print(f"Erro no login: {response.get('error', 'Erro desconhecido')}")
                self.show_error = True
                self.error_message = response.get("error", "Erro desconhecido no login")
        except Exception as e:
            print(f"Erro inesperado no login: {str(e)}")
            self.show_error = True
            self.error_message = f"Erro inesperado: {str(e)}"
    
    def update(self):
        if not self.logged_in:
            self.update_display()
            self.handle_input()
            
    def on_remove(self):
        # Não fechar o cliente aqui, pois ele será usado na GameScene
        pass 