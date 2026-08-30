# Verificador de arquivos duplicados

Ferramenta de terminal que percorre um diretório (e todas as subpastas) e encontra **imagens duplicadas**:

- **exatas** — o mesmo arquivo copiado (bytes idênticos);
- **visuais** — a mesma foto em outro formato, resolução ou compressão (por exemplo PNG original vs JPEG comprimido).

Em cada grupo, a ferramenta **mantém a de maior qualidade** e marca as demais para exclusão. Por padrão nada é apagado (simulação).

## Estratégia (e por que não comparar imagem com imagem)

Comparar cada par de fotos pixel a pixel seria O(n²) e muito lento. O fluxo usa filtros baratos primeiro:

1. **Inventário** — lista só arquivos de imagem, conta quantos são e soma o tamanho. Mostra o total e um **tempo estimado** antes de começar.
2. **SHA-256** — hash do arquivo inteiro, em paralelo. Cópias byte a byte caem no mesmo grupo sem abrir a imagem.
3. **pHash (hash perceptual)** — só para **conteúdos únicos** (um decode por SHA-256 diferente). Imagens iguais com JPEG ruim, outro tamanho ou outro formato ficam com hashes próximos.
4. **Agrupamento por distância de Hamming** — hashes de 64 bits são comparados com indexação em faixas (princípio da casa dos pombos), sem testar todos os pares quando a biblioteca cresce.
5. **Qualidade** — em cada grupo permanece a imagem com mais pixels; em empate, o arquivo maior; depois formatos menos destrutivos (PNG/TIFF acima de JPEG).

Isso evita decodificar a mesma cópia várias vezes e deixa a parte cara (abrir a foto) proporcional ao número de conteúdos distintos, não ao número de arquivos.

O tempo estimado usa taxas conservadoras (disco lento / fotos grandes). O tempo real é impresso no final.

## Requisitos

- Python **3.10 ou superior** (na prática use 3.12)
- Git (só se for clonar o repositório)

Formatos nesta versão: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`, `.tif`, `.tiff`, `.jfif`, `.jpe`.

HEIC/RAW ainda não entram.

### PowerShell ou Git Bash no Windows?

Dá para fazer **quase tudo no Git Bash**. Não é obrigatório usar PowerShell.

| O quê | Git Bash | PowerShell |
| --- | --- | --- |
| Instalar o Python | Baixar o instalador (passo 0) ou `winget` no PowerShell | Igual, ou `winget` direto |
| Criar venv, instalar, rodar `dupcheck` | Sim | Sim |
| `Set-ExecutionPolicy` | **Não precisa** | Só se `Activate.ps1` for bloqueado |

No Windows, o caminho do venv é sempre `.venv/Scripts/...` (no Linux/macOS é `.venv/bin/...`). Por isso o comando de ativar muda de terminal para terminal.

---

## Instalação (passo a passo)

Faça os passos **na ordem**, no **mesmo terminal**, sem pular linha no meio de um comando.

### 0) Instalar o Python (só na primeira vez naquele PC)

1. Baixe o instalador: [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Rode o `.exe`
3. **Marque** `Add python.exe to PATH` na primeira tela
4. Instale, **feche o terminal** e abra um **novo**

Confira (qualquer um destes deve imprimir `3.10` ou maior):

```bash
python --version
```

Se der `command not found` ou abrir a Microsoft Store:

```bash
python3 --version
py -3 --version
```

Ainda falhou? O Python não está no PATH. Reinstale marcando a opção acima, ou no **PowerShell**:

```powershell
winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
```

Abra outro terminal e teste `python --version` de novo.

### 1) Ir até a pasta do projeto

Git Bash (troque o caminho se o seu for outro):

```bash
cd /c/Repositórios/duplicated-file-verifier
```

PowerShell:

```powershell
cd C:\Repositórios\duplicated-file-verifier
```

Linux / macOS:

```bash
cd ~/duplicated-file-verifier
```

Se ainda não clonou:

```bash
git clone https://github.com/Filip3ra/duplicated-file-verifier.git
cd duplicated-file-verifier
```

### 2) Criar o ambiente virtual

O comando **não** é `venv`. É `python -m venv .venv`.

Git Bash / PowerShell no Windows:

```bash
python -m venv .venv
```

Se `python` falhar, tente:

```bash
python3 -m venv .venv
```

ou:

```bash
py -3 -m venv .venv
```

Linux / macOS:

```bash
python3 -m venv .venv
```

Isso cria a pasta `.venv` **dentro do projeto**. Só precisa uma vez por computador.

### 3) Ativar o ambiente

O prompt deve passar a mostrar `(.venv)`.

**Git Bash (Windows):**

```bash
source .venv/Scripts/activate
```

**PowerShell (Windows):**

```powershell
.\.venv\Scripts\Activate.ps1
```

Se o PowerShell recusar o script:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Depois rode o `Activate.ps1` de novo.

**Linux / macOS:**

```bash
source .venv/bin/activate
```

Para sair do ambiente depois: `deactivate`.

Não quer ativar? Pule o passo 3 e no passo 5 use o executável completo (está mais abaixo).

### 4) Instalar o programa e as dependências

Com o venv **já ativo** (`(.venv)` no prompt), ainda na pasta do projeto:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Espere terminar (baixa Pillow, numpy, scipy, etc.). Só precisa de novo se clonar o repo em outro PC ou apagar o `.venv`.

Confira:

```bash
dupcheck --version
```

Tem que aparecer algo como `dupcheck 0.1.0`. Se der `command not found`, o venv não está ativo: volte ao passo 3, ou use o caminho completo do passo 5.

### 5) Rodar

Primeiro comando: **só analisa** (não manda nada para a lixeira) e grava um plano.

**Git Bash** — use caminho estilo `/c/...` ou `C:/...`:

```bash
dupcheck "C:/Users/SEU_USUARIO/Pictures"
```

**PowerShell:**

```powershell
dupcheck "C:\Users\SEU_USUARIO\Pictures"
```

Ele mostra quantas imagens achou, um tempo estimado, e pergunta se continua. Depois lista `MANTER` / `DELETAR`.

Segundo comando: **não analisa de novo**. Envia à lixeira o que o último plano marcou. `--delete` vai **na mesma linha**:

```bash
dupcheck --delete
```

Confirme quando ele perguntar. Os arquivos vão para a **Lixeira**, não são apagados de vez.

#### Sem ativar o venv

Git Bash, na pasta do projeto:

```bash
.venv/Scripts/python.exe -m pip install --upgrade pip
.venv/Scripts/python.exe -m pip install -e .
.venv/Scripts/dupcheck.exe "C:/Users/SEU_USUARIO/Pictures"
.venv/Scripts/dupcheck.exe --delete
```

PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\dupcheck.exe "C:\Users\SEU_USUARIO\Pictures"
.\.venv\Scripts\dupcheck.exe --delete
```

### Outros comandos úteis

Analisar e enviar à lixeira no mesmo passo:

```bash
dupcheck "C:/Users/SEU_USUARIO/Pictures" --delete
```

Pular as perguntas:

```bash
dupcheck "C:/Users/SEU_USUARIO/Pictures" -y
dupcheck --delete -y
```

Só cópias **idênticas** (SHA-256), sem pHash — ainda só **imagens**:

```bash
dupcheck "C:/Users/SEU_USUARIO/Pictures" --method exact
```

SHA-256 em **qualquer tipo de arquivo** (PDF, DOCX, ZIP, txt, etc.):

```bash
dupcheck "C:/Users/SEU_USUARIO/Documentos" --method exact --all-files
```

`--all-files` entra na mesma linha. O `visual` continua valendo **apenas para imagens**, mesmo se você misturar os métodos:

```bash
dupcheck "C:/Users/SEU_USUARIO/Documentos" --method exact visual --all-files
```

Só imagens **parecidas** (pHash). `--threshold` só vale neste método:

```bash
dupcheck "C:/Users/SEU_USUARIO/Pictures" --method visual
dupcheck "C:/Users/SEU_USUARIO/Pictures" --method visual --threshold 4
```

Os dois métodos no mesmo comando (padrão, se você omitir `--method`):

```bash
dupcheck "C:/Users/SEU_USUARIO/Pictures" --method exact visual
```

No final o terminal mostra o tamanho analisado e o espaço marcado para a lixeira **separado por método** (exatas vs visuais) e o total.

Atalho antigo, equivalente a `--method exact`:

```bash
dupcheck "C:/Users/SEU_USUARIO/Pictures" --exact-only
```

### Se algo falhar

| Sintoma | Causa típica | O que fazer |
| --- | --- | --- |
| `python: command not found` ou abre a Store | Python não instalado / não está no PATH | Passo 0; feche e reabra o terminal |
| `venv: command not found` | `venv` não é um comando | Use `python -m venv .venv` |
| `Activate.ps1` bloqueado | Política do PowerShell | `Set-ExecutionPolicy` (só PowerShell) **ou** use Git Bash |
| `dupcheck: command not found` | venv inativo | `source .venv/Scripts/activate` (Git Bash) ou o `.exe` do passo 5 |
| `bash: --delete: command not found` | `--delete` numa linha sozinha | `dupcheck --delete` **junto**, um único comando |
| `pip` instala mas `dupcheck` não existe | `pip` do sistema, não do venv | Com o venv ativo: `python -m pip install -e .` |

## Testes (opcional)

Com o venv ativo:

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

### Opções úteis

| Opção | Função |
| --- | --- |
| `--delete` | Sem pasta: aplica o último plano. Com pasta: analisa e envia à lixeira |
| `--method exact` / `visual` | Um ou os dois. Padrão: `exact visual` |
| `--all-files` | No `exact`, inclui PDF, DOCX e qualquer outro arquivo (não só imagens) |
| `--exact-only` | Atalho de `--method exact` |
| `--threshold N` | Só no visual: distância máxima de Hamming (padrão 8). **0** = hashes iguais; **maior** = aceita fotos mais diferentes |
| `--workers N` | Processos em paralelo para hashing |
| `-y` / `--yes` | Não pergunta confirmação |
| `--include-hidden` | Inclui pastas e arquivos que começam com `.` |
| `--follow-symlinks` | Segue atalhos (desligado por padrão, para não entrar em loop) |
| `--quiet` | Sem barras de progresso |
| `--no-color` | Sem cores no terminal |

## Como ler o resultado

```
Grupo 1 — duplicatas visuais (distância perceptual até 4)
  MANTER   original.png     4000x3000    8.20 MB
  DELETAR  compressed.jpg   1920x1080    340.00 KB
```

`MANTER` é a melhor versão do grupo. `DELETAR` são as que `dupcheck --delete` enviaria à lixeira.

No rodapé aparece o **tamanho analisado** e o **espaço recuperável** por método (cópias exatas vs visuais) e o total.

## Distância visual (pHash / Hamming)

O método `visual` não compara pixel a pixel. Cada imagem vira um **hash perceptual de 64 bits** (pHash): um “resumo” da foto depois de reduzir e olhar frequências (DCT). Duas versões da mesma foto (JPEG ruim, outro tamanho, PNG vs JPG) tendem a hashes **parecidos**.

A **distância de Hamming** é quantos desses 64 bits diferem:

| Valor | Significado |
| --- | --- |
| **0** | Hashes iguais — quase certamente a mesma imagem |
| **1–8** | Muito parecidas (compressão, redimensionar leve). **8 é o padrão** |
| **12–16** | Mais permissivo: pode juntar fotos só semelhantes e gerar falso positivo |
| **64** | Todos os bits diferentes — imagens sem relação |

`--threshold N` é o **teto**: entram no mesmo grupo pares com distância **≤ N**.

- **Baixar** (ex.: 4) → mais restrito, menos grupos, menos risco de misturar fotos diferentes  
- **Subir** (ex.: 12) → mais grupos, mais chance de achar a mesma foto muito reencodada, e de juntar coisa que não é cópia  

O método `exact` ignora isso: só entra arquivo com os **mesmos bytes** (SHA-256). Uma foto salva de novo em JPEG **não** é exact.

## Limitações atuais

- Sem `--all-files`, a varredura padrão é só **imagens**. Com `--all-files`, o `exact` vale para qualquer arquivo; o `visual` continua só em imagens.
- Recortes, filtros pesados ou fotos só parecidas (mesmo lugar, outro clique) em geral **não** são o mesmo arquivo — o pHash não deve agrupá-los com o limiar padrão.
- A “menor qualidade” é uma heurística (resolução, tamanho, formato), não um índice fotográfico profissional.
