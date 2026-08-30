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

- Python **3.10** ou superior
- pip

Formatos nesta versão: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`, `.tif`, `.tiff`, `.jfif`, `.jpe`.

HEIC/RAW ainda não entram; a ideia é expandir para outros tipos de arquivo depois.

## Instalação

É necessário **Python 3.10+**. Se o comando `python` não funcionar no PowerShell, instale pelo [python.org](https://www.python.org/downloads/) (marque *Add python.exe to PATH*) ou:

```powershell
winget install Python.Python.3.12
```

Abra um terminal novo depois da instalação. Na pasta do repositório:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

Se a ativação do venv for bloqueada, use:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

Isso instala o comando `dupcheck`. Dependências de desenvolvimento (testes):

```powershell
pip install -e ".[dev]"
```

## Uso

Dois passos. Primeiro analisa e **grava um plano** (nada vai para a lixeira):

```powershell
dupcheck "C:\caminho\para\fotos"
```

Você verá quantas imagens existem, o tempo estimado, e os grupos MANTER / DELETAR.

Se a lista estiver certa, envie só o que já foi marcado — **sem analisar de novo**:

```powershell
dupcheck --delete
```

`--delete` vai **na mesma linha**. O comando mostra o último plano e pede confirmação antes de mandar para a lixeira.

Ainda dá para analisar e enviar num passo só:

```powershell
dupcheck "C:\caminho\para\fotos" --delete
```

Pular as perguntas (útil em script):

```powershell
dupcheck "C:\caminho\para\fotos" -y
dupcheck --delete -y
```

Só duplicatas idênticas, sem hash perceptual (mais rápido):

```powershell
dupcheck "C:\caminho\para\fotos" --exact-only
```

Equivalente sem instalar o comando:

```powershell
python -m duplicate_verifier "C:\caminho\para\fotos"
```

### Opções úteis

| Opção | Função |
| --- | --- |
| `--delete` | Sem pasta: aplica o último plano. Com pasta: analisa e envia à lixeira |
| `--exact-only` | Apenas SHA-256, sem comparação visual |
| `--threshold N` | Quão parecidas as fotos precisam ser (padrão: 8). Aumente se faltar match; diminua se juntar fotos diferentes |
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

`MANTER` é a melhor versão do grupo. `DELETAR` são as que `dupcheck --delete` enviaria à lixeira. Distância perceptual 0 costuma ser a mesma imagem; valores até o `--threshold` ainda entram como “a mesma foto”.

## Testes

```powershell
pip install -e ".[dev]"
pytest
```

## Limitações atuais

- Foco em **imagens**. Outros tipos de arquivo vêm depois (para documentos/binários o SHA-256 já resolve duplicata exata).
- Recortes, filtros pesados ou fotos só parecidas (mesmo lugar, outro clique) em geral **não** são o mesmo arquivo — o pHash não deve agrupá-los com o limiar padrão.
- A “menor qualidade” é uma heurística (resolução, tamanho, formato), não um índice fotográfico profissional.
