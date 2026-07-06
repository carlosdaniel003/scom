# SCOM

**Sistema de Entrada e Saída de Componentes Eletrônicos** para inventário técnico.

## Requisitos

- Python 3.10 ou superior
- PyQt6

## Instalação no Windows

```cmd
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m src.main
```

Também é possível executar `setup.bat` uma vez e depois usar `run.bat`.

## Recursos iniciais

- Dashboard de estoque
- Cadastro de peças com imagem
- Categorias com valor técnico obrigatório
- Sugestão e reaproveitamento de modelos cadastrados
- Inventário com pesquisa e filtros rápidos
- Registro de entradas e saídas
- Histórico de movimentações
- Banco local SQLite
