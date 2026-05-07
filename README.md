# HR Assistant

Assistant per la gestione e l'interrogazione semantica di curriculum vitae.
Carica i CV dalla cartella `resumes/`, li indicizza in un database vettoriale (ChromaDB)
e permette di interrogarli in linguaggio naturale tramite un'interfaccia Chainlit.

## Requisiti

- Python 3.12 o superiore
- [Poetry](https://python-poetry.org/) per la gestione delle dipendenze
- Una chiave API OpenAI

## Setup

1. Clonare/scaricare il progetto e posizionarsi nella cartella radice.

2. Installare le dipendenze:
```bash
   poetry install
```

3. Creare un file `.env` nella radice del progetto con la chiave OpenAI: OPENAI_API_KEY=sk-...


4. Inserire i CV da indicizzare nella cartella `resumes/`.
   Formati supportati: `.pdf`, `.docx`, `.txt`, `.zip` e altri formati Office.

## Avvio

```bash
poetry run chainlit run hr_assistant/__init__.py
```

L'applicazione sarà disponibile all'indirizzo `http://localhost:8000`.

Al primo avvio, i CV presenti in `resumes/` vengono processati e indicizzati
automaticamente; l'indice viene salvato in `data/chromadb/`.

## Struttura del progetto