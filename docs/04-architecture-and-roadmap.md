# 04 - Arquitetura Proposta e Roadmap

## Arquitetura alvo

```text
audio input
  -> preprocessing
  -> source separation
  -> transcription per stem
  -> symbolic cleanup
  -> quantization
  -> instrument/tab assignment
  -> internal score model
  -> .tg writer
  -> TuxGuitar validation
```

## Representacao interna

Antes de escrever `.tg`, o sistema deve converter tudo para uma representacao simbolica nossa:

```text
Project
  tempo_map
  time_signatures
  tracks[]

Track
  name
  instrument
  tuning
  notes[]

NoteEvent
  pitch_midi
  onset_seconds
  offset_seconds
  onset_tick
  duration
  velocity
  confidence
  string_index optional
  fret optional
  effects optional
  source_model
```

Motivo: cada modelo retorna coisas diferentes. Basic Pitch retorna note events/MIDI; MT3 retorna eventos multi-track; modelos de guitarra podem retornar string/fret; separadores retornam audio. A representacao interna desacopla tudo.

## MVP recomendado

### MVP 0 - Provar escrita .tg

Entrada: nenhuma, notas hardcoded.

Saida: `.tg` abrindo no TuxGuitar.

Escopo:

- uma guitarra;
- afinacao padrao;
- uma ou duas medidas;
- notas simples;
- sem efeitos.

Por que primeiro: se nao conseguimos escrever `.tg` validamente, a pesquisa de audio nao vira produto.

### MVP 1 - Audio de um instrumento para .tg

Entrada: WAV/MP3 com guitarra limpa, baixo ou piano solo.

Pipeline:

1. `Basic Pitch` gera MIDI/note events.
2. Detectar ou pedir BPM.
3. Quantizar eventos.
4. Se guitarra/baixo, atribuir string/fret por heuristica.
5. Escrever `.tg`.

Meta: tablatura simples e editavel, nao perfeita.

### MVP 2 - Stem separado para .tg

Entrada: musica completa.

Pipeline:

1. `Demucs`/`audio-separator` gera stems.
2. Escolher stem `guitar`, `bass` ou `piano`.
3. Rodar MVP 1 no stem escolhido.
4. Escrever uma ou mais tracks.

Meta: provar que source separation ajuda a transcricao.

### MVP 3 - Multi-track simples

Entrada: musica completa.

Pipeline:

1. Separar `drums`, `bass`, `guitar/piano/other`, `vocals`.
2. Transcrever baixo e guitarra.
3. Opcional: drums com Omnizart drum.
4. Gerar `.tg` multi-track.

Meta: arquivo TuxGuitar com varias tracks, mesmo que precise revisao manual.

### Fase avancada - Guitarra base vs solo

Aqui entram modelos monotimbrais, GuitarDuets-like, score-informed separation ou aprendizado com dados sinteticos. Nao deve ser promessa de MVP.

## Experimentos iniciais

### Experimento A - Qualidade de separacao

Modelos:

- Demucs `htdemucs`;
- Demucs `htdemucs_6s`;
- audio-separator/UVR com modelos relevantes;
- opcional: API AudioShake/Music.AI/LALAL.AI para benchmark comercial.

Audios:

- musica com guitarra limpa;
- rock com guitarra distorcida;
- musica com duas guitarras;
- baixo claro;
- piano + voz.

Resultados a salvar:

- stems WAV;
- tempo de inferencia;
- observacoes de bleeding;
- impacto no Basic Pitch.

### Experimento B - Transcricao de stem limpo

Modelos:

- Basic Pitch;
- Omnizart;
- se possivel MT3/YourMT3+.

Metricas:

- quantidade de notas espurias;
- qualidade ritmica apos quantizacao;
- facilidade de tocar;
- comparacao com MIDI/tab conhecido quando existir.

### Experimento C - MIDI-to-tab

Entrada: MIDI conhecido de guitarra.

Implementacoes:

- heuristica menor fret;
- heuristica com posicao de mao;
- depois comparar com paper MIDI-to-Tab.

Metricas:

- notas impossiveis;
- saltos grandes;
- diferenca contra tab real.

### Experimento D - Writer .tg

Validacoes:

- arquivo abre no TuxGuitar;
- TuxGuitar consegue salvar novamente;
- ZIP contem `version.txt` e `content.xml`;
- XML tem tracks, measures, beats e notes esperados.

## Dependencias candidatas

Audio:

- `librosa`: carregamento, features, beat/onset auxiliares.
- `soundfile`/`ffmpeg`: IO.
- `demucs`: source separation.
- `audio-separator`: testar modelos UVR.
- `basic-pitch`: audio -> MIDI/note events.
- `pretty_midi`: representacao MIDI intermediaria.
- `mido`: escrita/diagnostico MIDI.
- `music21`: manipulacao simbolica/MusicXML, se necessario.

TuxGuitar:

- writer proprio `.tg` 2.0 em Python.
- opcional: uma pequena ferramenta Java usando as classes oficiais do TuxGuitar, se a replica do schema ficar fragil.

## Novidades praticas para acompanhar

### Klangio Transcription Studio

Site: https://klang.io/transcription-studio/  
Plugin: https://klang.io/transcription-plugin/

Produto comercial que declara transcrever multi-instrumento e exportar MIDI/MusicXML/GuitarPro. Relevante como benchmark de produto, nao necessariamente como dependencia, porque nao encontrei uma API publica clara para integracao direta.

### AudioShake SDK/API

Developer portal: https://developer.audioshake.ai/  
SDK overview: https://developer.audioshake.ai/sdk/overview

Relevante porque oferece separacao, transcricao e SDK local. Bom candidato para comparar qualidade e latencia contra open-source.

### Music.AI API

Docs: https://music.ai/docs/api/reference/

Relevante por expor infraestrutura comercial da familia Moises. Pode ser fallback se qualidade open-source for insuficiente.

### LALAL.AI API

Docs: https://www.lalal.ai/api/v1/docs/

Relevante para stem separation comercial rapida, mas precisa avaliacao de custo, termos e qualidade por instrumento.

## Principais riscos do projeto

### Risco 1 - A qualidade do audio separado limita tudo

Se a guitarra separada tem voz/bateria vazando, o transcritor cria notas falsas. Separacao e transcricao precisam ser avaliadas juntas.

### Risco 2 - Transcricao gera MIDI nao musical

Mesmo com pitches corretos, o resultado pode ser ritmicamente ilegivel. Quantizacao e limpeza simbolica sao componentes de produto, nao detalhes.

### Risco 3 - Tablatura exige inferencia de execucao

Pitch correto nao diz qual corda usar. Uma tab tocavel precisa restricoes fisicas e preferencias musicais.

### Risco 4 - Direitos autorais e dados

Treinar ou processar musicas comerciais pode ter implicacoes legais dependendo do uso. Para desenvolvimento, preferir datasets com licenca clara.

### Risco 5 - Performance

Separacao de alta qualidade pode ser lenta e exigir GPU. O MVP deve aceitar batch offline antes de pensar em tempo real.

## Sequencia de trabalho sugerida

1. Implementar `tg_writer` minimo.
2. Implementar `NoteEvent` e conversor `NoteEvent -> .tg`.
3. Rodar Basic Pitch em audio solo e gerar `.tg`.
4. Adicionar quantizacao.
5. Adicionar heuristica MIDI-to-tab.
6. Rodar Demucs/audio-separator e conectar stems.
7. Criar corpus pequeno de testes com audio + referencia manual.
8. Avaliar modelos mais fortes: Omnizart, MT3/YourMT3+, guitar-specific.
9. Explorar lead/rhythm separation so depois dos passos acima.

## Definicao de sucesso para a primeira versao

Uma primeira versao boa nao precisa transcrever qualquer musica perfeitamente. Ela deve:

- gerar arquivo `.tg` valido;
- funcionar bem com audio solo ou stem limpo;
- produzir tablatura editavel;
- preservar timing basico;
- expor confianca/diagnostico para o usuario revisar;
- manter os intermediarios para depuracao.

## Backlog tecnico inicial

- Criar `src/` com pacote Python.
- Definir `pyproject.toml`.
- Implementar modelos de dados.
- Implementar writer `.tg` ZIP/XML.
- Adicionar fixtures de `.tg` minimo.
- Adicionar comando CLI `audio2tg`.
- Adicionar pipeline `basic-pitch -> internal model -> tg`.
- Adicionar docs de instalacao.
- Adicionar testes unitarios para XML/ZIP.

## Perguntas para decidir antes de codar alem do MVP

- Queremos output so de guitarra, ou multi-track completo?
- O usuario vai informar BPM/compasso, ou tentaremos detectar?
- O sistema deve priorizar fidelidade ou legibilidade da tablatura?
- Vamos mirar Windows local com GPU opcional?
- Vamos permitir APIs pagas como fallback?
