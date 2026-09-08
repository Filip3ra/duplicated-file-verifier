# Verificador de arquivos duplicados

Dá para usar de **duas formas** (o mesmo programa):

- **Terminal** — comando `dupcheck`
- **Janela gráfica** — `dupcheck --gui` ou `dupcheck-gui`

No Windows também dá para instalar pelo `dist/dupcheck-setup-0.1.0.exe` (atalho no Menu Iniciar; ver seção **Instalador Windows**).

Percorre um diretório (e as subpastas) e encontra duplicatas:

- **exatas** — o mesmo arquivo copiado (bytes idênticos), em imagens ou, com `--all-files`, em PDF, DOCX, etc.;
- **visuais** — a mesma foto em outro formato, resolução ou compressão (só imagens).

Em cada grupo **mantém a de maior qualidade** e marca o resto para a lixeira. Por padrão nada é apagado.

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
| Criar venv, instalar, rodar `dupcheck` / `dupcheck-gui` | Sim | Sim |
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

Tem que aparecer algo como `dupcheck 0.1.0`. Se der `command not found`, o venv não está ativo: volte ao passo 3, ou use o caminho completo no final desta seção.

### 5) Usar: janela ou terminal

Os dois jeitos ficam disponíveis depois do passo 4. O terminal **não é desligado** pela GUI.

#### Janela gráfica

```bash
dupcheck --gui
```

ou:

```bash
dupcheck-gui
```

Abrir já com uma pasta:

```bash
dupcheck --gui "C:/Users/SEU_USUARIO/Pictures"
```

Na tela: **Procurar** a pasta → conferir totais e o dropdown **Extensões** (todas marcadas; desmarque o que quiser ignorar) → **só imagens** ou **todos os arquivos** → marcar **cópias exatas** e/ou **visuais** → distância (se visual) → **Analisar** → conferir MANTER/DELETAR (clique na coluna **Ação**, Espaço, ou botão direito) → **Enviar cópias à lixeira**. Grupo todo em DELETAR fica cinza e é ignorado. Duplo clique numa linha abre a pasta no Explorer com o arquivo selecionado.

Sem ativar o venv (Git Bash, na pasta do projeto):

```bash
.venv/Scripts/dupcheck-gui.exe
```

PowerShell:

```powershell
.\.venv\Scripts\dupcheck-gui.exe
```

#### Terminal — lista de comandos

Troque o caminho pela pasta que você quer varrer. No Git Bash use `C:/...`; no PowerShell pode ser `C:\...`. `--delete` e `--all-files` vão **na mesma linha**.

| O que você quer | Comando |
| --- | --- |
| Abrir a janela | `dupcheck --gui` |
| Janela já na pasta | `dupcheck --gui "C:/Users/SEU_USUARIO/Pictures"` |
| Analisar imagens (exact + visual, padrão) | `dupcheck "C:/Users/SEU_USUARIO/Pictures"` |
| Só cópias idênticas (imagens) | `dupcheck "C:/Users/SEU_USUARIO/Pictures" --method exact` |
| Só imagens parecidas (pHash) | `dupcheck "C:/Users/SEU_USUARIO/Pictures" --method visual` |
| Visual mais restrito (só iguais) | `dupcheck "C:/Users/SEU_USUARIO/Pictures" --method visual --threshold 0` |
| Visual um pouco mais aberto | `dupcheck "C:/Users/SEU_USUARIO/Pictures" --method visual --threshold 2` |
| Exact + visual no mesmo run | `dupcheck "C:/Users/SEU_USUARIO/Pictures" --method exact visual` |
| SHA-256 em **qualquer** arquivo (PDF, DOCX, …) | `dupcheck "C:/Users/SEU_USUARIO/Documentos" --method exact --all-files` |
| Exact em tudo + visual só nas fotos | `dupcheck "C:/Users/SEU_USUARIO/Documentos" --method exact visual --all-files` |
| Enviar à lixeira o **último plano** (sem analisar de novo) | `dupcheck --delete` |
| Analisar e mandar à lixeira no mesmo passo | `dupcheck "C:/Users/SEU_USUARIO/Pictures" --delete` |
| Sem perguntar confirmação | `dupcheck "C:/Users/SEU_USUARIO/Pictures" -y` |
| Atalho antigo de `--method exact` | `dupcheck "C:/Users/SEU_USUARIO/Pictures" --exact-only` |

O primeiro `dupcheck "pasta"` **só analisa** e grava um plano. Ele mostra quantos arquivos achou, um tempo estimado, os grupos `MANTER` / `DELETAR` e o espaço recuperável (exatas vs visuais). Nada vai para a lixeira até `dupcheck --delete` (ou o botão na GUI).

#### Sem ativar o venv (só terminal)

Git Bash, na pasta do projeto:

```bash
.venv/Scripts/python.exe -m pip install --upgrade pip
.venv/Scripts/python.exe -m pip install -e .
.venv/Scripts/dupcheck.exe "C:/Users/SEU_USUARIO/Pictures"
.venv/Scripts/dupcheck.exe --delete
.venv/Scripts/dupcheck.exe --gui
```

PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\dupcheck.exe "C:\Users\SEU_USUARIO\Pictures"
.\.venv\Scripts\dupcheck.exe --delete
.\.venv\Scripts\dupcheck.exe --gui
```

### Se algo falhar

| Sintoma | Causa típica | O que fazer |
| --- | --- | --- |
| `python: command not found` ou abre a Store | Python não instalado / não está no PATH | Passo 0; feche e reabra o terminal |
| `venv: command not found` | `venv` não é um comando | Use `python -m venv .venv` |
| `Activate.ps1` bloqueado | Política do PowerShell | `Set-ExecutionPolicy` (só PowerShell) **ou** use Git Bash |
| `dupcheck: command not found` | venv inativo | `source .venv/Scripts/activate` (Git Bash) ou o `.exe` do passo 5 |
| `dupcheck-gui: command not found` | venv inativo ou install antigo | Ative o venv e rode de novo `python -m pip install -e .` |
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
| `--gui` | Abre a janela. Equivalente: `dupcheck-gui` |
| `--delete` | Sem pasta: aplica o último plano. Com pasta: analisa e envia à lixeira |
| `--method exact` / `visual` | Um ou os dois. Padrão: `exact visual` |
| `--all-files` | No `exact`, inclui PDF, DOCX e qualquer outro arquivo (não só imagens) |
| `--exact-only` | Atalho de `--method exact` |
| `--threshold N` | Só no visual. Padrão **1**. **0** = iguais; **1** = muito parecidas; **2** = um pouco parecidas |
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

## Instalador Windows (exe)

Gera a pasta `dist/dupcheck` (duplo clique em `dupcheck.exe`) e, se o [Inno Setup 6](https://jrsoftware.org/isinfo.php) estiver instalado, o `dist/dupcheck-setup-0.1.0.exe`.

```powershell
python -m pip install -e ".[package]"
python installer/build_windows.py
```

Sem o Inno Setup, o script ainda gera a pasta do app e pede para instalar o compilador:

```powershell
winget install JRSoftware.InnoSetup
python installer/build_windows.py --skip-bundle
```

O instalador copia o programa em `%LOCALAPPDATA%\dupcheck` (não precisa de admin), cria atalho no Menu Iniciar e oferece atalho na área de trabalho. `dupcheck.exe` abre a janela; `dupcheck-cli.exe` é o terminal (`dupcheck-cli --help`).

Só o bundle, sem instalador:

```powershell
python installer/build_windows.py --skip-installer
```

## Distância visual (pHash / Hamming)

O método `visual` não compara pixel a pixel. Cada imagem vira um **hash perceptual de 64 bits** (pHash): um “resumo” da foto depois de reduzir e olhar frequências (DCT). Duas versões da mesma foto (JPEG ruim, outro tamanho, PNG vs JPG) tendem a hashes **parecidos**.

A **distância de Hamming** é quantos desses 64 bits diferem:

| Valor | Significado |
| --- | --- |
| **0** | Imagens iguais |
| **1** | Imagens muito parecidas (**padrão**) |
| **2** | Imagens um pouco parecidas |
| **maior** | Mais permissivo; aumenta o risco de juntar fotos que não são a mesma |

`--threshold N` é o **teto**: entram no mesmo grupo pares com distância **≤ N**.

- **0** → só imagens iguais  
- **1** (padrão) → muito parecidas  
- **2 ou mais** → aceita pares um pouco (ou bem) diferentes; sobe o risco de falso positivo

O método `exact` ignora isso: só entra arquivo com os **mesmos bytes** (SHA-256). Uma foto salva de novo em JPEG **não** é exact.

## Limitações atuais

- Sem `--all-files`, a varredura padrão é só **imagens**. Com `--all-files`, o `exact` vale para qualquer arquivo; o `visual` continua só em imagens.
- Recortes, filtros pesados ou fotos só parecidas (mesmo lugar, outro clique) em geral **não** são o mesmo arquivo — o pHash não deve agrupá-los com o limiar padrão.
- A “menor qualidade” é uma heurística (resolução, tamanho, formato), não um índice fotográfico profissional.
