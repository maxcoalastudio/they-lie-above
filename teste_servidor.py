from network_manager import NetworkManager
import time
import random

def testar_conexao():
    print("Iniciando teste de conexão com o Firebase...")
    
    # Criar instância do NetworkManager
    network = NetworkManager()
    
    if network.connected:
        print("✅ Conectado ao Firebase com sucesso!")
        
        # Criar email aleatório para teste
        random_num = random.randint(1, 10000)
        email = f"teste{random_num}@teste.com"
        password = "123456"
        
        print(f"\nTestando com o email: {email}")
        
        # Testar registro de usuário
        print("\nTestando registro de usuário...")
        sucesso, usuario = network.register(email, password)
        
        if not sucesso and "EMAIL_EXISTS" in str(usuario):
            print("ℹ️ Usuário já existe, tentando login direto...")
            sucesso = True
            usuario = None
        
        if sucesso:
            # Testar login
            print("\nTestando login...")
            sucesso_login, usuario_login = network.login(email, password)
            if sucesso_login:
                print("✅ Login realizado com sucesso!")
                
                # Testar atualização de posição
                print("\nTestando atualização de posição...")
                network.update_player_position(
                    usuario_login.uid,
                    [10.0, 20.0, 30.0],  # posição teste
                    [0.0, 0.0, 0.0]      # rotação teste
                )
                print("✅ Posição atualizada com sucesso!")
                
                # Testar atualização de score
                print("\nTestando atualização de score...")
                network.update_score(usuario_login.uid, 100)
                print("✅ Score atualizado com sucesso!")
                
                # Testar busca de outros jogadores
                print("\nTestando busca de outros jogadores...")
                outros_jogadores = network.get_other_players()
                print(f"✅ Jogadores encontrados: {len(outros_jogadores) if outros_jogadores else 0}")
                
                # Testar leaderboard
                print("\nTestando leaderboard...")
                leaderboard = network.get_leaderboard()
                if leaderboard:
                    print("✅ Leaderboard recuperado com sucesso!")
                    print("\nTop jogadores:")
                    for player_id, data in leaderboard.items():
                        print(f"Jogador {player_id}: {data['score']} pontos")
                else:
                    print("ℹ️ Leaderboard vazio")
                
            else:
                print(f"❌ Erro no login: {usuario_login}")
        else:
            print(f"❌ Erro no registro: {usuario}")
    else:
        print("❌ Erro ao conectar ao Firebase")

if __name__ == "__main__":
    testar_conexao() 