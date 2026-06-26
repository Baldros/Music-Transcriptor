# 06 - MVP Audio Monofonico para Contrato

## Objetivo

Implementar a primeira versao da camada:

```text
audio monofonico -> eventos de nota -> MelodyScoreContract -> .tg
```

O alvo aqui nao e musica completa. E uma melodia simples, preferencialmente um instrumento ou voz isolada, com BPM informado pelo usuario.

## Decisao tecnica

Comecar com dois backends:

- `librosa-pyin`: baseline CPU, simples e bem documentado.
- `torchaudio`: backend opcional com suporte a CUDA para pitch tracking.

Nao usar GPU para tudo no MVP. A parte pesada e estimar F0 por frame; a segmentacao, quantizacao, insercao de pausas e montagem do contrato sao leves e ficam em Python puro.

## Por que nao so librosa

`librosa.pyin` implementa pYIN: calcula candidatos de F0 e usa Viterbi para estimar a sequencia mais provavel de pitch/voicing. Isso e bom para melodia monofonica limpa, mas roda em CPU.

Fonte: https://librosa.org/doc/main/generated/librosa.pyin.html

## Por que incluir torchaudio

`torchaudio.functional.detect_pitch_frequency` declara suporte a CPU e CUDA. Ele usa normalized cross-correlation function com median smoothing. Isso e util para aproveitar a RTX local sem ainda introduzir modelos maiores.

Fonte: https://docs.pytorch.org/audio/2.6.0/generated/torchaudio.functional.detect_pitch_frequency.html

## Alternativas melhores para depois

### CREPE / torchcrepe

CREPE e um pitch tracker monofonico baseado em rede convolucional diretamente sobre waveform. O `torchcrepe` e uma implementacao PyTorch com pesos convertidos. E um bom candidato para melhorar robustez em audio real, especialmente voz/instrumento solo com vibrato ou ruido.

Fontes:

- https://github.com/marl/crepe
- https://github.com/maxrmorrison/torchcrepe

### Basic Pitch

Basic Pitch ja e audio-to-MIDI e lida melhor com instrumentos polifonicos simples. Continua sendo interessante como backend alternativo, principalmente para comparar contra o pipeline proprio de F0 -> notas. Para este MVP, preferimos controlar a fronteira `eventos -> contrato`.

Fonte: https://github.com/spotify/basic-pitch

## Pipeline implementado

1. Carregar audio.
2. Estimar F0 por frames.
3. Converter frequencia para MIDI.
4. Agrupar frames voiced consecutivos em eventos de nota.
5. Quantizar onset/offset usando BPM informado.
6. Inserir pausas explicitas.
7. Dividir eventos por compasso.
8. Dividir duracoes em figuras aceitas pelo TuxGuitar.
9. Mapear `pitch_midi` para `string`/`fret`.
10. Gerar `MelodyScoreContract`.
11. Reusar o writer `.tg`.

## Comandos

Instalacao baseline CPU:

```powershell
py -3.11 -m pip install -e ".[audio]"
```

Instalacao com PyTorch/torchaudio:

```powershell
py -3.11 -m pip install -e ".[audio,torch]"
```

Se `torch.cuda.is_available()` voltar `False`, usar o seletor oficial do PyTorch para escolher o wheel CUDA correto para Windows:

https://pytorch.org/get-started/locally/

Gerar `.tg` com `librosa.pyin`:

```powershell
audio-to-tg input.wav out\melody.tg --bpm 120 --backend librosa-pyin --instrument guitar
```

Gerar `.tg` tentando CUDA via `torchaudio`:

```powershell
audio-to-tg input.wav out\melody.tg --bpm 120 --backend torchaudio --device cuda --instrument guitar
```

Salvar tambem o contrato intermediario para debug:

```powershell
audio-to-tg input.wav out\melody.tg --bpm 120 --contract-output out\melody.contract.json
```

## Limitacoes atuais

- BPM precisa ser informado.
- So suporta melodia monofonica.
- Nao detecta articulacao, bends, slides ou vibrato como efeitos de guitarra.
- A escolha string/fret usa menor fret disponivel; ainda nao modela posicao de mao.
- A segmentacao por pitch ainda e heuristica simples.
- O backend `torchaudio` nao fornece probabilidade de voicing; o MVP combina frequencia detectada com limiar de RMS.

## Proximos ajustes praticos

- Gerar audios sinteticos de teste para validar F0 end-to-end.
- Adicionar backend `torchcrepe`.
- Adicionar deteccao ou estimativa assistida de BPM.
- Melhorar segmentacao com onset detection.
- Adicionar heuristica de mao/posicao para string/fret.
