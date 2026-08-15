# Deploy na Oracle Cloud VM (HTTP via IP público)

Guia para subir o ERP numa instância **Oracle Cloud Always Free** usando Docker Compose.
Acesso por `http://SEU-IP-PUBLICO` (sem domínio). Migração para HTTPS ao final.

---

## 1. Criar a instância

- Compute → Instances → **Create Instance**.
- Shape: **VM.Standard.A1.Flex** (ARM, Always Free) — 1–2 OCPU / 6–12 GB é suficiente.
  Imagem **Ubuntu 22.04** (ou Oracle Linux 9).
- Salve a chave SSH. Anote o **IP público**.

## 2. Abrir a porta 80 na VCN (Security List)

Networking → Virtual Cloud Network → sua VCN → **Security Lists** → Default →
**Add Ingress Rules**:

| Campo | Valor |
|------|-------|
| Source CIDR | `0.0.0.0/0` |
| IP Protocol | TCP |
| Destination Port Range | `80` |

## 3. Conectar e instalar o Docker

```bash
ssh -i sua-chave.key ubuntu@SEU-IP-PUBLICO

# Docker + plugin compose
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker compose version
```

### Swap de 2 GB — ESSENCIAL na Micro de 1 GB ⚠️

A VM.Standard.E2.1.Micro (1 GB / 1 OCPU) vem **sem swap**. O ERP roda numa boa em
~600–700 MB, mas o **build** das imagens pode estourar a RAM e ser morto (OOM). Adicione swap:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h   # confira: deve mostrar 2,0Gi de Swap
```

Com swap, `docker compose ... up -d --build` roda estável (só um pouco mais lento). Nada
mais precisa mudar — não é necessário buildar no CI.

## 4. Liberar a porta 80 no firewall da instância ⚠️

As imagens Oracle vêm com o firewall **bloqueando tudo além do SSH**. Sem este passo,
a porta 80 fica inacessível mesmo com a regra da VCN.

**Ubuntu (iptables):**
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo netfilter-persistent save
```

**Oracle Linux (firewalld):**
```bash
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --reload
```

## 5. Clonar o repo e configurar segredos

```bash
# na VM (repo público -> não precisa de credencial):
cd ~
git clone https://github.com/bgodii/ecommerce_erp.git
cd ecommerce_erp
cp .env.production.example .env.production
nano .env.production   # defina POSTGRES_PASSWORD, JWT_SECRET (openssl rand -hex 32)
                       # e CORS_ORIGINS=["http://SEU-IP-PUBLICO"]
```

> `.env.production` fica **só na VM** (é gitignored). O deploy automático nunca o sobrescreve.

### ⚠️ Evite subir o compose de DEV por engano

Um `docker compose up -d` **sem `-f`** usa o `docker-compose.yml` (desenvolvimento): publica o front
na **8090** em vez da 80 e tenta conectar no banco com a senha padrão `erp` — o que derruba o site com
502/"password authentication failed". Para blindar, crie na VM um `.env` que fixa o compose de produção:

```bash
cd ~/ecommerce_erp
{ echo "COMPOSE_FILE=docker-compose.prod.yml"; grep -v '^COMPOSE_FILE=' .env.production; } > .env
chmod 600 .env
```

Com isso, `docker compose up -d`, `docker compose ps` e `logs` já apontam para produção — sem precisar
lembrar dos parâmetros. (O `.env` é gitignored e o CD continua funcionando normalmente.)

## 6. Levar seus dados atuais para a VM (recomendado)

Se você já usou o sistema e quer manter tudo (login, produtos, vendas, canais) **sem redigitar**,
os dados vêm do **banco** (não da planilha). Use `pg_dump` → `psql`:

1. Gere o backup na sua máquina (ou use o que já foi gerado em `~/erp-backup-AAAA-MM-DD.sql`):
```bash
docker compose exec -T db pg_dump -U erp -d erp --no-owner --no-privileges > erp-backup.sql
```
2. Envie para a VM:
```bash
scp -i sua-chave.key erp-backup.sql ubuntu@SEU-IP-PUBLICO:~/
```
3. Na VM, restaure **uma única vez** com o script protegido (ele **aborta se já houver dados**, então
   nunca sobrescreve por engano):
```bash
cd ~/ecommerce_erp
bash deploy/restore-once.sh ~/erp-backup.sql
```
> Mantenha `POSTGRES_USER=erp` e `POSTGRES_DB=erp` no `.env.production` para o restore casar. O dump já
> traz o schema + a versão das migrations, então a API não vai remigrar. (Pule esta etapa se for começar do zero.)
>
> **Importante:** isto roda **só nesta primeira vez**. Os deploys automáticos (CD) **nunca** rodam restore
> nem resetam o banco — o volume do Postgres persiste entre deploys.

## 7. Subir tudo

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

A API roda `alembic upgrade head` no start (sem efeito se você restaurou o backup — já está na versão certa).

Acesse **http://SEU-IP-PUBLICO**:
- **Restaurou o backup** → entre com **suas credenciais atuais** (mesmo e-mail/senha de antes; a senha é
  preservada e independe do `JWT_SECRET`).
- **Começando do zero** → **Criar minha loja**.

### Alternativa: começar do zero e importar sua planilha
A planilha **não vem no repositório** (dados reais). Para popular a partir dela:
```bash
# copie sua planilha para a VM e rode:
docker compose --env-file .env.production -f docker-compose.prod.yml \
  exec api python -m app.seed_xlsx --xlsx /caminho/sua-planilha.xlsx --email voce@email.com --password suasenha --org "Minha Loja"
```

## 8. CD automático — deploy a cada push (GitHub Actions)

O workflow `.github/workflows/deploy.yml` roda os **testes** e, se passarem, faz **deploy na VM por SSH**
a cada push na `main`. Ele nunca reseta seus dados — só `git pull` + `docker compose up -d --build`
(via `deploy/deploy.sh`).

**a) Crie uma chave SSH de deploy** (na sua máquina):
```bash
ssh-keygen -t ed25519 -f erp_deploy -N "" -C "github-actions-deploy"
# autorize a chave na VM:
ssh-copy-id -i erp_deploy.pub ubuntu@SEU-IP-PUBLICO
# (ou cole o conteúdo de erp_deploy.pub em ~/.ssh/authorized_keys na VM)
```

**b) Cadastre os Secrets no GitHub** (repo → Settings → Secrets and variables → Actions):

| Secret | Valor |
|--------|-------|
| `SSH_HOST` | IP público da VM |
| `SSH_USER` | `ubuntu` (ou `opc` no Oracle Linux) |
| `SSH_KEY` | conteúdo da chave **privada** `erp_deploy` (o arquivo inteiro) |
| `SSH_PORT` | `22` (opcional) |

**c) Faça um push:**
```bash
git push origin main
```
O GitHub roda os testes → conecta na VM → atualiza e reconstrói. Acompanhe na aba **Actions**.

> Pré-requisitos na VM: repo clonado em `~/ecommerce_erp` (passo 5) e `.env.production` configurado.
> Migrations são aplicadas no start da API (aditivas — não resetam dados).

## Operação

```bash
# logs
docker compose -f docker-compose.prod.yml logs -f api

# atualizar o código -> AUTOMÁTICO via push na main (CD). Manual, se precisar:
bash deploy/deploy.sh

# backup do banco (rode de tempos em tempos!)
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U erp -d erp --no-owner --no-privileges > backup_$(date +%F).sql
```

## HTTPS com domínio (quando tiver um domínio) — já vem pronto

Já existe tudo no repo: `docker-compose.https.yml` (adiciona o **Caddy**) e `deploy/Caddyfile`.
O Caddy pega o **certificado SSL sozinho** (Let's Encrypt) e renova automático. Passos:

**1. Aponte o domínio para a VM (DNS).** No seu registrador (ex.: registro.br), crie um
**registro A** apontando para o IP público da VM:
```
Tipo A   Nome @      Valor 136.248.114.139   (domínio raiz)
Tipo A   Nome erp    Valor 136.248.114.139   (se quiser usar erp.elucrocerto.com.br)
```

**2. Abra a porta 443** na **VCN (Security List, ingress TCP 443)** e no **firewall da VM**:
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

**3. Configure o domínio no `.env.production`** (na VM):
```bash
# adicione/edite:
DOMAIN=elucrocerto.com.br
CORS_ORIGINS=["https://elucrocerto.com.br"]
```

**4. Suba com o compose de HTTPS:**
```bash
docker compose --env-file .env.production -f docker-compose.https.yml up -d --build
```
Acesse **https://elucrocerto.com.br** — cadeado válido, sem configurar certificado. Os **dados são
preservados** (usa o mesmo volume do banco).

**5. (Opcional) Deixe o CD usar HTTPS.** Para o deploy automático usar o compose de HTTPS,
crie na VM um arquivo `.env.deploy` (fica só na VM, é gitignored):
```bash
echo 'COMPOSE_FILE=docker-compose.https.yml' > ~/ecommerce_erp/.env.deploy
```
A partir daí, cada push faz deploy em HTTPS.

> Dica: o Caddy vira instalável como PWA de verdade (o ícone da tela inicial já funciona no HTTP,
> mas o prompt "Instalar app" aparece no HTTPS).
