# 01 - Separacao de Instrumentos

## Problema

Separar instrumentos de uma musica mixada e Music Source Separation (MSS), tambem chamada de stem separation ou demixing. O caso mais comum e separar em `vocals`, `drums`, `bass` e `other`. O nosso projeto precisa de algo mais dificil: separar guitarra, baixo, bateria, voz, piano e, idealmente, separar partes parecidas entre si, como guitarra base e guitarra solo.

Isso ultimo e separacao monotimbral: fontes com timbre muito parecido. A literatura recente aponta que esse caso ainda e subexplorado, especialmente com guitarras tocando juntas.

## Tecnicas usadas

### Modelos por mascara em espectrograma

A abordagem classica moderna converte audio para uma representacao tempo-frequencia, geralmente STFT ou CQT, e o modelo prediz mascaras para cada fonte. Depois se reconstrui o audio com a fase do sinal original ou uma estimativa refinada.

Familias comuns:

- U-Net/TFC-TDF U-Net: fortes para espectrogramas.
- Open-Unmix: baseline LSTM em magnitude STFT.
- Spleeter: U-Net/encoder-decoder em TensorFlow.
- Band-split models: dividem o espectro em bandas e modelam relacoes temporais/frequenciais.
- Transformers/RoPE: BS-RoFormer troca partes recorrentes por atencao com Rotary Position Embedding.

### Modelos em waveform e hibridos

Demucs comeca mais proximo do dominio de waveform e evolui para Hybrid Demucs e Hybrid Transformer Demucs, combinando waveform e espectrograma. Isso e relevante porque transientes de guitarra/bateria e fase importam para modelos de transcricao posteriores.

### Separacao condicionada/informada

Em vez de pedir "separe tudo", alguns trabalhos condicionam o modelo por instrumento, atividade temporal, partitura ou notas estimadas. Isso e interessante para o nosso caso porque:

- podemos primeiro detectar instrumentos;
- depois separar apenas o instrumento alvo;
- depois usar notas estimadas para melhorar a separacao.

Papers como Jointist e GuitarDuets exploram ligacoes entre separacao e transcricao.

## Ferramentas open-source praticas

### Demucs / Hybrid Transformer Demucs

Repositorio: https://github.com/facebookresearch/demucs

Uso provavel no MVP: primeira camada de separacao.

Pontos fortes:

- Qualidade alta para 4 stems.
- Modelo v4 usa Hybrid Transformer Demucs.
- Tem modelo experimental de 6 fontes com `guitar` e `piano`.

Riscos:

- O repositorio original informa que nao esta mais ativamente mantido.
- O proprio README diz que a fonte `piano` no modelo de 6 stems tem bleeding/artifacts; guitarra fica "okay", mas ainda nao e garantida.
- Mesmo quando ha `guitar`, isso nao resolve guitarra base vs solo.

### Spleeter

Repositorio: https://github.com/deezer/spleeter

Uso provavel: baseline rapido, especialmente para comparar com Demucs.

Pontos fortes:

- Muito simples de usar.
- Modelos 2, 4 e 5 stems: vocal/acompanhamento, vocal/drums/bass/other, vocal/drums/bass/piano/other.
- Historicamente muito usado.

Riscos:

- Mais antigo.
- Dependencia TensorFlow.
- Nao separa guitarra explicitamente nos modelos principais.
- Pode ser bom como primeira camada, mas nao deve ser a base final se quisermos guitarra detalhada.

### Open-Unmix

Docs: https://sigsep.github.io/open-unmix/  
Repositorio: https://github.com/sigsep/open-unmix-pytorch

Uso provavel: baseline academico e ferramenta de comparacao.

Pontos fortes:

- Implementacao de referencia.
- Facil de entender e adaptar.
- Pre-treinado em MUSDB18 para 4 stems.

Riscos:

- Hoje tende a ficar atras de Demucs/BS-RoFormer em qualidade.
- Nao e focado em separacao fina de guitarras.

### audio-separator / Ultimate Vocal Remover

audio-separator PyPI: https://pypi.org/project/audio-separator/  
UVR: https://github.com/Anjok07/ultimatevocalremovergui

Uso provavel: wrapper pratico para testar varios modelos rapidamente.

Pontos fortes:

- Exposicao Python/CLI para modelos usados pelo ecossistema UVR.
- Pode ser mais produtivo para prototipagem que integrar cada modelo manualmente.

Riscos:

- Ecossistema menos academico e mais "tooling".
- Licencas/pesos/modelos precisam ser conferidos caso a caso.
- A reprodutibilidade cientifica pode ser menor que Demucs/Open-Unmix.

### Torchaudio HDEMUCS

Docs: https://docs.pytorch.org/audio/main/generated/torchaudio.pipelines.HDEMUCS_HIGH_MUSDB.html

Uso provavel: caminho mais integrado ao PyTorch para inferencia com Hybrid Demucs.

Pontos fortes:

- API padronizada.
- Menos dependencia de scripts externos.

Riscos:

- O ecossistema torchaudio vem mudando e algumas APIs podem entrar em manutencao/deprecacao.

## Modelos e papers recentes relevantes

### BS-RoFormer

Paper: https://arxiv.org/abs/2309.02612

Ideia: usar band-split em espectrograma complexo e Transformers hierarquicos com RoPE para estimar mascaras por banda. O paper reporta lideranca no Sound Demixing Challenge 2023 e forte SDR em MUSDB18-HQ.

Relevancia: provavel familia de modelos a considerar quando quisermos qualidade maxima, mas treinamento/inferencia podem ser pesados.

### SCNet

Paper: https://arxiv.org/abs/2401.13276

Ideia: separar o espectro em subbandas e comprimir de forma esparsa para reduzir custo computacional. Reporta boa relacao qualidade/custo.

Relevancia: candidato para inferencia mais leve, se houver implementacao/pesos confiaveis.

### Moises-Light

Paper: https://arxiv.org/html/2510.06785v1

Ideia: arquitetura leve com band-splitting, RoPE e encoder-decoder inspirados por trabalhos recentes. O paper aponta BS-RoFormer como estado da arte e tenta reduzir parametros drasticamente.

Relevancia: acompanhar. Pode ser importante se quisermos rodar localmente em maquinas comuns.

### GuitarDuets

Paper: https://arxiv.org/html/2507.01172v1

Ideia: dataset e framework para separar duetos de violao/classical guitar, com foco monotimbral. O paper destaca que a maioria da pesquisa trata instrumentos diferentes, nao duas fontes parecidas.

Relevancia: diretamente ligado ao problema "guitarra base vs guitarra solo", mas ainda e pesquisa recente e nao solucao pronta para rock/metal/pop.

### Jointist

Paper: https://arxiv.org/abs/2302.00286

Ideia: framework conjunto para reconhecimento de instrumento, transcricao e separacao. A separacao usa informacao de instrumento e resultados de transcricao.

Relevancia: arquitetura conceitual boa para fases futuras: separacao e transcricao devem conversar, nao ser etapas totalmente isoladas.

## Datasets importantes

### MUSDB18 / MUSDB18-HQ

MUSDB18: https://zenodo.org/records/1117372  
MUSDB18-HQ: https://zenodo.org/records/3338373

Dataset padrao com 150 musicas e stems `vocals`, `drums`, `bass`, `other`. Bom para baseline, ruim para guitarra detalhada porque guitarra normalmente cai em `other`.

### MoisesDB

Paper: https://arxiv.org/abs/2307.15913  
Repositorio: https://github.com/moises-ai/moises-db

Dataset com 240 tracks, 45 artistas e 12 generos, organizado em taxonomia hierarquica alem de 4 stems. Mais alinhado ao nosso objetivo que MUSDB18.

### Slakh2100

Site: https://www.slakh.com/  
Zenodo: https://zenodo.org/records/4599666

Dataset sintetico com audio multitrack e MIDI alinhado. Muito util para treinar/avaliar separacao e transcricao, mas tem gap de dominio porque e sintetico.

### MedleyDB

Site: https://medleydb.weebly.com/  
NYU: https://steinhardt.nyu.edu/marl/research/resources/medleydb

Multitracks royalty-free com anotacoes MIR. Bom para tarefas com fontes individuais, instrument activations e melody f0.

### GuitarSet

Repositorio: https://github.com/marl/guitarset/  
Zenodo: https://zenodo.org/records/3371780

Dataset de guitarra solo com captacao hexafonica, anotacoes ricas e audio por string. Mais importante para transcricao de guitarra que para separacao de musica completa.

### URMP

Site: https://labsites.rochester.edu/air/projects/URMP.html

Pecas multi-instrumentais coordenadas com faixas individuais, MIDI e video. Mais classico/acustico, mas util para separacao/transcricao multi-instrumento.

## APIs comerciais

### AudioShake

Docs: https://developer.audioshake.ai/

Oferece API para source separation, transcription e analise de conteudo. E interessante para comparar qualidade contra stack open-source e eventualmente para fallback comercial.

### Music.AI / Moises

Docs API: https://music.ai/docs/api/reference/

Moises tem produto final para musicos e a plataforma Music.AI para API. Relevante porque a empresa tambem publicou MoisesDB.

### LALAL.AI API

Docs: https://www.lalal.ai/api/v1/docs/

API publica para stem separation e processamento de audio. Relevante para prototipagem rapida, mas precisamos avaliar custo, limites e termos.

## Riscos tecnicos

- Bleeding: vazamento de outros instrumentos no stem separado.
- Artefatos: degradam pitch tracking e transcricao.
- Guitarras distorcidas: harmonicos densos confundem f0/multipitch.
- Dobras em unissono ou oitavas: duas guitarras tocando notas proximas podem parecer uma fonte so.
- Reverb/delay: cria caudas e falsos onsets.
- Live recordings: vazamento de microfone e ruido pioram separacao.

## Recomendacao para o projeto

1. Comecar com Demucs `htdemucs` e `htdemucs_6s`, comparando com `audio-separator`.
2. Medir stems por ouvido e por impacto na transcricao, nao apenas por SDR.
3. Para guitarra, aceitar inicialmente um stem `guitar` combinado.
4. Separar lead/rhythm so depois de termos um bom transcritor por stem.
5. Guardar sempre os stems intermediarios para depuracao.

## Consultas em ingles usadas

- `music source separation instrument separation guitar accompaniment solo guitar paper automatic music transcription 2025`
- `Demucs music source separation official GitHub Hybrid Transformer Demucs paper`
- `BS-RoFormer music source separation paper GitHub`
- `MoisesDB dataset music source separation paper official`
- `Classical Guitar Duet Separation using GuitarDuets`
- `AudioShake API source separation official documentation`
