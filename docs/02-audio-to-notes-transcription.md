# 02 - Transcricao Audio para Notas, MIDI e Tablatura

## Problema

Converter audio em notas nao e apenas encontrar uma "frequencia dominante + tempo".

Uma nota util para TuxGuitar precisa, no minimo:

- pitch ou MIDI note number;
- onset;
- offset/duracao;
- metrica/quantizacao;
- velocity/dinamica aproximada;
- instrumento/track;
- para guitarra/baixo: string e fret;
- tecnicas: bend, slide, hammer-on, pull-off, palm mute, vibrato, dead note etc.

Em musica polifonica ha varias notas simultaneas, cada uma com harmonicos. Em guitarra, a mesma nota pode aparecer em mais de uma corda, entao pitch nao determina tablatura.

## Subproblemas

### Pitch e multipitch

- Monofonico: uma fonte de pitch por vez. Mais facil. Ferramentas como CREPE, pYIN e YIN funcionam melhor aqui.
- Polifonico: acordes, sobreposicoes e varias notas simultaneas. Precisa de AMT neural ou multipitch estimation.
- Multi-instrumento: alem de notas, precisa atribuir cada nota a um instrumento.

### Onset/offset

Onset e o inicio perceptivo da nota. Offset e o fim. Ambos podem ser ambiguos: em piano ha pedal, em guitarra ha sustain, vibrato, slides e ruído de corda. O paper do AMT Challenge 2025 ressalta que ate a definicao de onset/offset depende de convencoes de avaliacao.

### Quantizacao

Modelos de AMT geralmente produzem tempos continuos ou MIDI "sujo". Para tablatura legivel, precisamos transformar em valores musicais: semicolcheia, colcheia pontuada, tercinas, ligaduras etc.

TuxGuitar tambem tem uma grade interna propria. A conversao nao deve depender apenas de segundos; precisa de tempo, compasso e resolucao.

### Tablatura para guitarra

Tablatura e um problema extra:

- escolher afinacao;
- escolher string/fret para cada pitch;
- evitar saltos impossiveis;
- representar acordes tocaveis;
- inferir tecnicas de execucao.

Mesmo com MIDI perfeito, ainda existe o problema MIDI-to-tab.

## Ferramentas open-source praticas

### Basic Pitch

Repositorio: https://github.com/spotify/basic-pitch  
Demo: https://basicpitch.spotify.com/

Uso provavel: MVP para audio de um instrumento ou stem limpo.

Pontos fortes:

- Instalavel via `pip`.
- Gera MIDI, CSV de note events e pitch bends.
- Instrument-agnostic.
- Funciona melhor com um instrumento por vez.
- Tem runtimes TensorFlow/CoreML/TFLite/ONNX.

Riscos:

- Em mix completo tende a gerar notas demais.
- Nao separa instrumentos.
- Nao resolve tablatura string/fret.
- MIDI pode precisar de limpeza/quantizacao pesada.

### Omnizart

Repositorio: https://github.com/Music-and-Culture-Technology-Lab/omnizart  
Docs: https://music-and-culture-technology-lab.github.io/omnizart-doc/

Uso provavel: baseline multi-modulo para notas, vocal, drums, chords e beat.

Pontos fortes:

- Biblioteca Python focada em AMT.
- Suporta pitched instruments, vocal melody, chords, drums e beat.
- Fornece checkpoints pre-treinados.

Riscos:

- Dependencias podem ser pesadas.
- Precisa validar manutencao e compatibilidade no Windows.
- Transcricao generica pode nao ser ideal para guitarra distorcida.

### MT3

Repositorio: https://github.com/magenta/mt3  
Paper: https://arxiv.org/pdf/2111.03017

Uso provavel: referencia para multi-instrument AMT.

Pontos fortes:

- Modelo Transformer multi-task/multitrack.
- Paper mostra melhora em instrumentos low-resource como guitarra.
- Conceitualmente alinhado ao nosso problema.

Riscos:

- O repositorio diz que nao e produto oficialmente suportado pelo Google.
- Treinamento nao e simples.
- Inferencia via Colab/checkpoints pode ser menos amigavel que Basic Pitch.
- Ainda gera MIDI/eventos, nao `.tg`.

### YourMT3+

Repositorio: https://github.com/mimbres/YourMT3  
Paper: https://arxiv.org/abs/2407.04822

Uso provavel: acompanhar/testar quando formos atacar multi-instrumento seriamente.

Pontos fortes:

- Baseado na familia MT3.
- Usa encoder mais forte, Mixture of Experts e augmentations com stems.
- O paper reporta competitividade em varios datasets.

Riscos:

- Ainda pode ser mais pesquisa que pacote produtivo.
- Precisamos validar pesos, licenca e facilidade de inferencia.

### MR-MT3

Paper: https://arxiv.org/abs/2403.10024  
Codigo: https://github.com/gudgud96/MR-MT3

Uso provavel: referencia para um erro importante: instrument leakage.

Pontos fortes:

- Ataca fragmentacao de notas entre instrumentos.
- Introduz metricas para instrument leakage e instrument detection.

Riscos:

- Pesquisa recente; integracao em produto pode ser trabalhosa.

### Onsets and Frames

Site: https://magenta.withgoogle.com/onsets-frames  
Codigo: https://github.com/magenta/magenta/blob/main/magenta/models/onsets_frames_transcription/README.md

Uso provavel: referencia historica e baseline para piano/drums.

Pontos fortes:

- Modelo classico para piano polifonico.
- Ideia central boa: prever onsets e frames separadamente.

Riscos:

- Foco em piano/drums, nao guitarra.
- O repositorio Magenta foi arquivado em 2026 e esta read-only.

### Librosa, Essentia, madmom, CREPE

librosa: https://librosa.org/doc/  
CREPE: https://github.com/marl/crepe  
Essentia: https://essentia.upf.edu/  
madmom: https://github.com/CPJKU/madmom

Uso provavel: features, analise, pre/post-processamento, tempo/beat/onsets e pitch monofonico.

Pontos fortes:

- Excelentes para construir ferramentas auxiliares.
- Uteis para validar e depurar saidas de modelos neurais.

Riscos:

- Nao resolvem AMT polifonico completo sozinhos.
- CREPE e pYIN sao melhor usados em stems monofonicos/solo.

## Guitarra e tablatura

### GuitarSet

Repositorio: https://github.com/marl/guitarset/  
Paper: https://archives.ismir.net/ismir2018/paper/000188.pdf

Dataset de guitarra com captacao hexafonica. Importante porque fornece informacao por corda, permitindo treinar modelos que aprendem string/fret, nao apenas pitch.

### TabCNN

Paper: https://archives.ismir.net/ismir2019/paper/000033.pdf  
Codigo: https://github.com/andywiggins/tab-cnn

Ideia: estimar tablatura diretamente de audio de guitarra solo usando CNN em CQT. A vantagem e prever fingering/corda, nao apenas pitch.

Relevancia: forte referencia para um modulo de guitarra solo, mas nao resolve mix completo.

### Note-level automatic guitar transcription com attention

Paper: https://eurasip.org/Proceedings/Eusipco/Eusipco2022/pdfs/0000229.pdf

Ideia: attention mechanism, beat-informed quantization e multi-task learning para gerar transcricao note-level, nao apenas frame-level.

Relevancia: muito alinhado ao nosso problema de transformar audio em notacao legivel.

### Automatic Guitar Transcription With Deep Neural Networks

Paper: https://mir.dei.uc.pt/pdf/Journals/MERGE/Access_2025_Chieppa.pdf

Ideia: replica e analisa modelo com self-attention e beat-informed quantisation; discute anotacoes frame-level/note-level e conversao MIDI pitch -> fret relativo a corda.

Relevancia: paper recente e diretamente conectado a tablatura. Vale ler com calma antes de treinar algo proprio.

### SynthTab e DadaGP

SynthTab paper: https://arxiv.org/html/2309.09085v3  
SynthTab repo: https://github.com/yongyizang/SynthTab  
DadaGP repo: https://github.com/dada-bots/dadaGP  
DadaGP paper: https://arxiv.org/abs/2107.14653

Ideia: gerar audio sintetico a partir de tablaturas GuitarPro, criando dataset grande com anotacao perfeita de tab.

Relevancia: caminho pratico para treinar modelos de tablatura sem depender so de GuitarSet. O risco e domain gap: som sintetico nao e som real mixado.

### MIDI-to-Tab

Paper: https://arxiv.org/html/2408.05024v1

Mesmo se a transcricao gerar MIDI bom, ainda precisamos transformar MIDI em tablatura. Abordagens com Transformer e datasets grandes de tabs podem ajudar a escolher string/fret de forma musical.

## Bibliotecas para representacao simbolica

### pretty_midi

Repositorio: https://github.com/craffel/pretty-midi

Bom para criar/manipular MIDI com notas em segundos, instrumentos e velocities. Excelente representacao intermediaria.

### mido

Docs: https://mido.readthedocs.io/

Bom para escrever MIDI bruto, mensagens, eventos e tracks.

### music21

Docs: https://music21.org/music21docs/  
PyPI: https://pypi.org/project/music21/

Bom para representacao musical, MusicXML, analise harmonica e manipulacao simbolica. Menos focado em tablatura.

### PyGuitarPro

Docs: https://pyguitarpro.readthedocs.io/  
Repositorio: https://github.com/perlence/pyguitarpro

Le e escreve GP3/GP4/GP5. Pode ser util como formato intermediario, mas nao escreve `.tg` nativo.

## Avaliacao

Metricas tecnicas:

- note onset F1;
- note offset F1;
- frame F1;
- multipitch F1;
- instrument detection F1;
- instrument leakage ratio;
- string/fret accuracy para guitarra;
- edit distance entre tablaturas;
- quantidade de correcao manual necessaria.

Metricas praticas:

- A tablatura abre no TuxGuitar?
- A reproducao MIDI soa parecida?
- Um guitarrista consegue tocar?
- Ritmo esta legivel?
- Quantas notas espurias por compasso?

## Recomendacao para o projeto

1. Definir uma representacao interna: `Track -> NoteEvent(pitch, onset, offset, velocity, instrument, confidence, optional string/fret/effects)`.
2. Comecar com Basic Pitch em audio mono/stem limpo.
3. Adicionar quantizacao com beat/tempo estimado.
4. Para guitarra, implementar primeiro heuristica MIDI-to-tab simples:
   - afinacao padrao;
   - menor fret possivel;
   - limite de alcance por posicao;
   - penalidade para saltos grandes.
5. Depois testar modelo guitar-specific com GuitarSet/SynthTab.
6. So entao atacar multi-instrumento com MT3/YourMT3+/separacao previa.

## Consultas em ingles usadas

- `automatic music transcription polyphonic audio to MIDI latest model paper 2024 2025`
- `Basic Pitch Spotify audio to MIDI official GitHub paper`
- `MT3 multi task multitrack music transcription official GitHub paper`
- `guitar tablature transcription deep learning dataset TabCNN GuitarSet paper`
- `automatic guitar tablature transcription deep learning conformer beat-informed quantisation paper github`
- `MR-MT3 Memory Retaining Multi-Track Music Transcription instrument leakage paper 2024`
