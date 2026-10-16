# CashPath — guia para testar o aplicativo

Este guia é para quem recebeu o código-fonte e quer executar o CashPath em uma instalação limpa. O teste tem duas partes: iniciar a API (backend) e, em outro terminal, iniciar o app Flutter.

## O que você precisa

- Python 3.10 ou superior;
- Flutter com Dart 3.13.5 ou superior;
- Android Studio com Android SDK e um emulador Android, ou um celular Android com depuração USB;
- internet para baixar as dependências;
- configurações de SMTP para testar cadastro com email e senha;
- configurações OAuth do Google para testar login Google.

O código deve estar organizado com as pastas `backend/` e `frontend/`. Se elas tiverem outros nomes, ajuste os caminhos dos comandos abaixo.

## 1. Instalar as ferramentas

### Windows

1. Instale [Python 3.10+](https://www.python.org/downloads/).
2. Instale o [Flutter](https://docs.flutter.dev/install), escolhendo Windows como sistema e Android como plataforma de destino. Adicione o diretório `flutter/bin` ao `Path`, conforme o guia.
3. Instale o [Android Studio](https://developer.android.com/studio/install), conclua a instalação do Android SDK e crie um emulador Android.

### Windows com WSL 2 (Ubuntu)

O backend pode ser executado no WSL, enquanto o Flutter e o Android Emulator ficam no Windows.

1. Abra o terminal Ubuntu do WSL. Se Python e `venv` não estiverem instalados, execute:

   ```bash
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip
   ```

2. Instale Flutter e Android Studio no Windows seguindo as instruções da seção Windows.
3. Para melhor desempenho, mantenha o código do backend no sistema de arquivos do WSL (por exemplo, `~/projetos/CashPath`), não em `/mnt/c`.

### Linux (Ubuntu/Debian)

1. Instale Python e as ferramentas para criar o ambiente virtual:

   ```bash
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip
   ```

2. Instale o [Flutter](https://docs.flutter.dev/install), escolhendo Linux como sistema e Android como destino.
3. Instale o [Android Studio](https://developer.android.com/studio/install), o Android SDK e crie um emulador.

### macOS

1. Instale [Python 3.10+](https://www.python.org/downloads/).
2. Instale o [Flutter](https://docs.flutter.dev/install), escolhendo macOS como sistema e Android como destino.
3. Para testar no Android, instale o [Android Studio](https://developer.android.com/studio/install), o Android SDK e crie um emulador.

## 2. Preparar o backend

Abra um terminal na pasta `backend`.

### Windows — PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Se o PowerShell impedir a ativação do ambiente virtual, execute o comando abaixo na mesma janela e tente ativá-lo novamente:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### WSL 2, Linux e macOS

Na pasta `backend`, execute:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

## 3. Configurar email e login Google

Abra `backend/.env`. O campo `JWT_SECRET_KEY` é obrigatório. Gere uma chave localmente com:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Cole o resultado em `JWT_SECRET_KEY` no `.env`. No PowerShell, use o mesmo comando depois de ativar o ambiente virtual.

Para o cadastro por email e senha, preencha `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` e `SMTP_FROM` com as credenciais de um serviço de envio de email. Para testar login Google, preencha `GOOGLE_CLIENT_ID` com o client ID de servidor correspondente ao configurado em `frontend/lib/config/google_config.dart`. Se o projeto OAuth estiver em modo de teste, a conta Google usada no teste precisa estar autorizada nele.

Essas credenciais não são fornecidas no código-fonte. Se você não tiver suas próprias configurações, solicite ao responsável pelo projeto as credenciais ou instruções de teste. Sem SMTP, o servidor inicia, mas o cadastro que exige código de confirmação não termina. Sem OAuth, o login Google não funciona. Não compartilhe o arquivo `.env`.

O backend carrega `backend/.env` automaticamente. Não é preciso executar `source .env`.

## 4. Iniciar a API

Com o ambiente virtual ativado e ainda dentro da pasta `backend`, execute:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

No Windows, WSL, Linux e macOS, o comando é igual. Deixe esse terminal aberto durante o teste. Para confirmar que a API iniciou, abra `http://127.0.0.1:8000/docs` no navegador. Para encerrar, pressione `Ctrl+C`.

## 5. Iniciar o app

Abra um **segundo terminal** na pasta `frontend`. Confirme que o emulador está iniciado ou que o celular está conectado e execute:

```bash
flutter doctor
flutter pub get
flutter devices
flutter run
```

Se `flutter doctor` apontar componentes ausentes, instale-os antes de continuar. No Windows, Linux e macOS, o Android Studio fornece o SDK e o emulador Android.

### Conexão do app com a API

O endereço fica em `frontend/lib/config/api_config.dart`. A configuração incluída aponta para `http://10.0.2.2:8000`, que é o endereço usado pelo emulador Android para acessar a API executada no computador.

| Onde o app está rodando | Endereço local típico |
|---|---|
| Emulador Android | `http://10.0.2.2:8000` |
| Celular Android na mesma rede Wi-Fi | `http://IP_DO_COMPUTADOR:8000` |
| App desktop no mesmo computador | `http://127.0.0.1:8000` |

Se usar celular físico, substitua o endereço em `api_config.dart` pelo IP local do computador, mantenha os dois dispositivos na mesma rede e libere a porta 8000 no Firewall. Se o backend estiver no WSL 2 e o emulador não conseguir acessá-lo, verifique o encaminhamento de portas do WSL e o Firewall do Windows.

## O que esperar na primeira execução

O banco `financas.db` não precisa vir com o pacote. Se não existir, a API o cria na pasta `backend`, monta as tabelas, executa as migrações e adiciona as categorias fixas. O app começa sem contas, renda, transações, orçamentos ou metas. Crie uma conta e insira os dados durante o teste.

## Se algo não funcionar

- **A API não inicia:** confirme que `JWT_SECRET_KEY` foi preenchida e que o ambiente virtual está ativado.
- **O app informa que não consegue conectar:** confirme que a API está rodando, revise `api_config.dart` e verifique o Firewall.
- **O cadastro não envia o código:** confira as configurações SMTP e os logs do terminal da API.
- **O login Google falha:** confira o client ID do servidor, o client ID configurado no Flutter e se a conta está autorizada como usuária de teste no Google Cloud.
- **`flutter` não é reconhecido:** confirme que `flutter/bin` foi adicionado ao `Path` e reabra o terminal.

## Arquivos do banco

- `backend/schema.sql`: cria a estrutura inicial;
- `backend/migrations/`: atualiza a estrutura de bancos existentes;
- `backend/app/database.py`: inicializa o banco e inclui as categorias fixas;
- `backend/scripts/promote_admin.py`: promove uma conta já criada para administradora, quando necessário.
