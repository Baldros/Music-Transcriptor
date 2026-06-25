# 05 - Contrato Camada 2 -> Camada 3

## Objetivo

Este documento define o contrato rigido entre:

- fim da camada 2: `audio -> dados musicais simbolicos`;
- inicio da camada 3: `dados musicais simbolicos -> arquivo .tg`.

A camada 3 nao deve receber audio, espectrograma, frequencias ou eventos soltos em segundos. Ela deve receber uma partitura intermediaria ja normalizada, quantizada e validavel.

Nome de trabalho do contrato:

```text
MelodyScoreContract v0.1.0
```

## Decisao principal

O writer `.tg` nao deve fazer inferencia musical pesada.

Ele pode:

- validar estrutura;
- converter o contrato para XML do TuxGuitar;
- empacotar `version.txt` e `content.xml`;
- preencher defaults mecanicos, quando explicitamente definidos neste contrato.

Ele nao deve:

- detectar BPM;
- quantizar audio;
- decidir se uma nota e colcheia ou semicolcheia;
- escolher string/fret a partir de MIDI, exceto em uma ferramenta auxiliar anterior ao contrato;
- criar pausas para tapar buracos ritmicos;
- corrigir nota impossivel;
- separar compassos;
- interpretar expressividade de audio.

Essas responsabilidades pertencem a camada 2 ou a uma etapa intermediaria de limpeza simbolica antes da fronteira do contrato.

## Escopo do v0.1.0

O contrato v0.1.0 mira o primeiro MVP funcional:

- uma ou mais tracks de instrumento de cordas com trastes;
- afinacao explicita por track;
- uma voz ritmica por track;
- notas monofonicas ou acordes simples;
- pausas explicitas;
- tempo e formula de compasso definidos por compasso;
- duracoes quantizadas em valores aceitos pelo TuxGuitar;
- efeitos opcionais simples.

Fora do escopo do v0.1.0:

- bateria/percussao;
- multiplas vozes independentes na mesma track;
- mudancas de tempo no meio do compasso;
- tuplets complexos gerados automaticamente;
- bends detalhados por curva;
- ligaduras expressivas ambiguas;
- dedilhado/mao direita;
- letras;
- repeticoes, casas alternativas e marcadores avancados.

Esses itens podem entrar em versoes futuras do contrato.

## Unidade de tempo canonica

O contrato usa tempo musical inteiro, nao segundos nem floats.

```json
{
  "units_per_quarter": 720720
}
```

No v0.1.0, `units_per_quarter` deve ser sempre `720720`, porque esse valor mapeia diretamente para a escala precisa usada pelo TuxGuitar atual.

Consequencias:

- uma seminima vale `720720`;
- uma minima vale `1441440`;
- uma semibreve vale `2882880`;
- uma colcheia vale `360360`;
- uma semicolcheia vale `180180`.

O inicio musical do projeto e `0`.

Ao escrever o XML do TuxGuitar, o writer soma o offset interno do TuxGuitar:

```text
tg_preciseStart = 720720 + measure.start_units + event.offset_units
```

Motivo: no modelo do TuxGuitar, a primeira batida da musica comeca em um quarto de nota interno, nao em zero.

## Estrutura geral

Formato recomendado: JSON.

```json
{
  "contract": {
    "name": "MelodyScoreContract",
    "version": "0.1.0"
  },
  "producer": {
    "name": "audio-to-score-pipeline",
    "version": "0.0.1"
  },
  "project": {
    "title": "Example melody",
    "artist": "",
    "album": "",
    "author": "",
    "transcriber": "generated",
    "comments": "",
    "units_per_quarter": 720720,
    "tempo_map": [],
    "time_signatures": [],
    "key_signatures": []
  },
  "tracks": []
}
```

Campos de topo:

- `contract`: identifica o contrato.
- `producer`: identifica a ferramenta/modelo que gerou o arquivo.
- `project`: metadados e grade musical global.
- `tracks`: tracks musicais que serao escritas no `.tg`.

Campos desconhecidos so podem aparecer dentro de objetos `extensions`. O writer v0.1.0 deve rejeitar campos desconhecidos fora desses pontos para evitar ambiguidade.

## Project

### project.title

Tipo: `string`.

Titulo da musica no TuxGuitar.

### project.units_per_quarter

Tipo: `integer`.

Obrigatorio. No v0.1.0 deve ser `720720`.

### project.tempo_map

Lista de tempos.

No v0.1.0, mudancas de tempo so podem ocorrer no inicio de um compasso.

```json
[
  {
    "measure": 1,
    "bpm": 120,
    "beat_unit": 4
  }
]
```

Campos:

- `measure`: compasso onde o tempo passa a valer, iniciando em `1`.
- `bpm`: inteiro positivo.
- `beat_unit`: unidade do pulso; no MVP usar `4`.

### project.time_signatures

Lista de formulas de compasso.

```json
[
  {
    "measure": 1,
    "numerator": 4,
    "denominator": 4
  }
]
```

No v0.1.0, cada mudanca deve ocorrer no inicio de um compasso.

### project.key_signatures

Lista de armaduras.

```json
[
  {
    "measure": 1,
    "value": 0
  }
]
```

No MVP, `value` pode ser sempre `0`.

## Track

Exemplo:

```json
{
  "id": "guitar_1",
  "name": "Guitar",
  "kind": "fretted-string",
  "instrument": {
    "gm_bank": 0,
    "gm_program": 25,
    "channel_name": "Steel String Acoustic Guitar 1"
  },
  "tuning": [
    { "string": 1, "pitch_midi": 64 },
    { "string": 2, "pitch_midi": 59 },
    { "string": 3, "pitch_midi": 55 },
    { "string": 4, "pitch_midi": 50 },
    { "string": 5, "pitch_midi": 45 },
    { "string": 6, "pitch_midi": 40 }
  ],
  "max_fret": 24,
  "clef": "treble",
  "measures": []
}
```

Campos:

- `id`: identificador estavel interno.
- `name`: nome da track no TuxGuitar.
- `kind`: no v0.1.0, usar `fretted-string`.
- `instrument`: programa General MIDI usado para playback.
- `tuning`: afinacao explicita, da corda mais aguda para a mais grave.
- `max_fret`: maior casa permitida.
- `clef`: no MVP, usar `treble`.
- `measures`: compassos da track.

### Afinacao padrao de guitarra

```json
[
  { "string": 1, "pitch_midi": 64 },
  { "string": 2, "pitch_midi": 59 },
  { "string": 3, "pitch_midi": 55 },
  { "string": 4, "pitch_midi": 50 },
  { "string": 5, "pitch_midi": 45 },
  { "string": 6, "pitch_midi": 40 }
]
```

### Afinacao padrao de baixo

```json
[
  { "string": 1, "pitch_midi": 43 },
  { "string": 2, "pitch_midi": 38 },
  { "string": 3, "pitch_midi": 33 },
  { "string": 4, "pitch_midi": 28 }
]
```

## Measure

Cada track deve ter um objeto `measure` para cada compasso global da musica.

```json
{
  "number": 1,
  "start_units": 0,
  "duration_units": 2882880,
  "events": []
}
```

Campos:

- `number`: numero do compasso, iniciando em `1`.
- `start_units`: inicio absoluto do compasso, em unidades musicais.
- `duration_units`: duracao total do compasso.
- `events`: eventos ritmicos da voz principal.

Para 4/4:

```text
duration_units = 4 * 720720 = 2882880
```

Para 3/4:

```text
duration_units = 3 * 720720 = 2162160
```

Para 6/8:

```text
duration_units = 6 * 720720 * 4 / 8 = 2162160
```

## Event

Um `event` representa um `TGBeat` na camada `.tg`.

Ele pode conter:

- uma nota;
- varias notas simultaneas, formando acorde;
- nenhuma nota, representando pausa.

Exemplo de nota:

```json
{
  "id": "m1_e1",
  "offset_units": 0,
  "duration": {
    "value": 4,
    "dots": 0,
    "tuplet": { "enters": 1, "times": 1 },
    "units": 720720
  },
  "notes": [
    {
      "pitch_midi": 60,
      "string": 2,
      "fret": 1,
      "velocity": 90,
      "tied": false,
      "effects": [],
      "confidence": {
        "overall": 0.94,
        "pitch": 0.97,
        "onset": 0.92,
        "duration": 0.88,
        "tab_position": 1.0
      },
      "source": {
        "onset_seconds": 0.0,
        "offset_seconds": 0.5,
        "stem_id": "guitar_1"
      }
    }
  ]
}
```

Exemplo de pausa:

```json
{
  "id": "m1_rest1",
  "offset_units": 720720,
  "duration": {
    "value": 4,
    "dots": 0,
    "tuplet": { "enters": 1, "times": 1 },
    "units": 720720
  },
  "notes": []
}
```

Campos:

- `id`: identificador estavel para debug.
- `offset_units`: posicao dentro do compasso.
- `duration`: duracao musical quantizada.
- `notes`: lista de notas simultaneas. Lista vazia significa pausa.

No v0.1.0, os eventos de cada compasso devem cobrir o compasso inteiro, sem buracos e sem sobreposicao.

Exemplo em 4/4 com quatro seminimas:

```text
event 1: offset 0,       duration 720720
event 2: offset 720720,  duration 720720
event 3: offset 1441440, duration 720720
event 4: offset 2162160, duration 720720
fim:     2882880
```

## Duration

```json
{
  "value": 4,
  "dots": 0,
  "tuplet": { "enters": 1, "times": 1 },
  "units": 720720
}
```

Campos:

- `value`: denominador musical. Valores aceitos: `1`, `2`, `4`, `8`, `16`, `32`, `64`.
- `dots`: `0`, `1` ou `2`.
- `tuplet.enters`: numero de notas que entram no espaco.
- `tuplet.times`: numero de notas equivalentes ocupadas.
- `units`: duracao final em unidades canonicas.

Formula de validacao:

```text
base_units = units_per_quarter * 4 / value

dot_factor:
  dots = 0 -> 1
  dots = 1 -> 3/2
  dots = 2 -> 7/4

duration.units = base_units * dot_factor * tuplet.times / tuplet.enters
```

Exemplos:

```json
{ "value": 4, "dots": 0, "tuplet": { "enters": 1, "times": 1 }, "units": 720720 }
```

Seminima.

```json
{ "value": 8, "dots": 0, "tuplet": { "enters": 1, "times": 1 }, "units": 360360 }
```

Colcheia.

```json
{ "value": 4, "dots": 1, "tuplet": { "enters": 1, "times": 1 }, "units": 1081080 }
```

Seminima pontuada.

```json
{ "value": 8, "dots": 0, "tuplet": { "enters": 3, "times": 2 }, "units": 240240 }
```

Tercina de colcheia.

## Note

```json
{
  "pitch_midi": 64,
  "string": 1,
  "fret": 0,
  "velocity": 90,
  "tied": false,
  "effects": [],
  "confidence": {
    "overall": 0.98
  },
  "source": {
    "onset_seconds": 1.0,
    "offset_seconds": 1.5,
    "stem_id": "guitar_1"
  }
}
```

Campos obrigatorios:

- `pitch_midi`: nota MIDI, inteiro de `0` a `127`.
- `string`: corda, iniciando em `1`.
- `fret`: casa, iniciando em `0`.
- `velocity`: inteiro de `1` a `127`.
- `tied`: booleano.
- `effects`: lista, pode ser vazia.

Campos opcionais:

- `confidence`: confianca dos modelos da camada 2.
- `source`: informacao de rastreabilidade do audio original.
- `extensions`: dados extras ignorados pelo writer v0.1.0.

Regra obrigatoria para tracks `fretted-string`:

```text
pitch_midi == tuning[string].pitch_midi + fret
```

Exemplo:

```text
string 2 = MIDI 59
fret 1   = +1
pitch    = 60
```

Logo:

```json
{
  "pitch_midi": 60,
  "string": 2,
  "fret": 1
}
```

e valido.

## Effects

No v0.1.0, `effects` e uma lista de strings simples.

Valores aceitos:

```json
[
  "vibrato",
  "deadNote",
  "slide",
  "hammer",
  "ghostNote",
  "accentuatedNote",
  "heavyAccentuatedNote",
  "palmMute",
  "staccato",
  "tapping",
  "slapping",
  "popping",
  "fadeIn",
  "letRing"
]
```

Efeitos estruturados devem ficar em `extensions` ate uma versao futura do contrato.

Exemplo futuro, ainda nao consumido pelo writer v0.1.0:

```json
{
  "effects": ["bend"],
  "extensions": {
    "bend": {
      "points": [
        { "position": 0, "value": 0 },
        { "position": 6, "value": 4 }
      ]
    }
  }
}
```

## Exemplo completo minimo

Melodia: C4, D4, E4, F4 em quatro seminimas, guitarra padrao, 120 BPM, 4/4.

```json
{
  "contract": {
    "name": "MelodyScoreContract",
    "version": "0.1.0"
  },
  "producer": {
    "name": "manual-example",
    "version": "0.0.1"
  },
  "project": {
    "title": "Four notes",
    "artist": "",
    "album": "",
    "author": "",
    "transcriber": "generated",
    "comments": "",
    "units_per_quarter": 720720,
    "tempo_map": [
      { "measure": 1, "bpm": 120, "beat_unit": 4 }
    ],
    "time_signatures": [
      { "measure": 1, "numerator": 4, "denominator": 4 }
    ],
    "key_signatures": [
      { "measure": 1, "value": 0 }
    ]
  },
  "tracks": [
    {
      "id": "guitar_1",
      "name": "Guitar",
      "kind": "fretted-string",
      "instrument": {
        "gm_bank": 0,
        "gm_program": 25,
        "channel_name": "Steel String Acoustic Guitar 1"
      },
      "tuning": [
        { "string": 1, "pitch_midi": 64 },
        { "string": 2, "pitch_midi": 59 },
        { "string": 3, "pitch_midi": 55 },
        { "string": 4, "pitch_midi": 50 },
        { "string": 5, "pitch_midi": 45 },
        { "string": 6, "pitch_midi": 40 }
      ],
      "max_fret": 24,
      "clef": "treble",
      "measures": [
        {
          "number": 1,
          "start_units": 0,
          "duration_units": 2882880,
          "events": [
            {
              "id": "m1_e1",
              "offset_units": 0,
              "duration": {
                "value": 4,
                "dots": 0,
                "tuplet": { "enters": 1, "times": 1 },
                "units": 720720
              },
              "notes": [
                {
                  "pitch_midi": 60,
                  "string": 2,
                  "fret": 1,
                  "velocity": 90,
                  "tied": false,
                  "effects": []
                }
              ]
            },
            {
              "id": "m1_e2",
              "offset_units": 720720,
              "duration": {
                "value": 4,
                "dots": 0,
                "tuplet": { "enters": 1, "times": 1 },
                "units": 720720
              },
              "notes": [
                {
                  "pitch_midi": 62,
                  "string": 2,
                  "fret": 3,
                  "velocity": 90,
                  "tied": false,
                  "effects": []
                }
              ]
            },
            {
              "id": "m1_e3",
              "offset_units": 1441440,
              "duration": {
                "value": 4,
                "dots": 0,
                "tuplet": { "enters": 1, "times": 1 },
                "units": 720720
              },
              "notes": [
                {
                  "pitch_midi": 64,
                  "string": 1,
                  "fret": 0,
                  "velocity": 90,
                  "tied": false,
                  "effects": []
                }
              ]
            },
            {
              "id": "m1_e4",
              "offset_units": 2162160,
              "duration": {
                "value": 4,
                "dots": 0,
                "tuplet": { "enters": 1, "times": 1 },
                "units": 720720
              },
              "notes": [
                {
                  "pitch_midi": 65,
                  "string": 1,
                  "fret": 1,
                  "velocity": 90,
                  "tied": false,
                  "effects": []
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

## Mapeamento para XML do TuxGuitar

### Arquivo .tg

O writer gera um ZIP:

```text
output.tg
  version.txt
  content.xml
```

`version.txt`:

```text
TuxGuitar_file_format 2.0.0
```

### Project -> TGSong

Campos:

- `project.title` -> `<name>`
- `project.artist` -> `<artist>`
- `project.album` -> `<album>`
- `project.author` -> `<author>`
- `project.transcriber` -> `<transcriber>`
- `project.comments` -> `<comments>`

### Tempo/time signature -> TGMeasureHeader

Para cada compasso global:

```xml
<TGMeasureHeader>
  <timeSignature denominator="4" numerator="4"/>
  <tempo>120</tempo>
</TGMeasureHeader>
```

Se tempo ou formula nao mudaram, o writer ainda pode repetir o header por compasso, seguindo o modelo do TuxGuitar.

### Track -> TGTrack

```xml
<TGTrack maxFret="24">
  <name>Guitar</name>
  <channelId>2</channelId>
  <color B="0" G="0" R="255"/>
  <TGString>64</TGString>
  <TGString>59</TGString>
  <TGString>55</TGString>
  <TGString>50</TGString>
  <TGString>45</TGString>
  <TGString>40</TGString>
  <TGLyric from="1"/>
  ...
</TGTrack>
```

### Measure -> TGMeasure

```xml
<TGMeasure>
  <clef>treble</clef>
  <keySignature>0</keySignature>
  ...
</TGMeasure>
```

### Event -> TGBeat

Para cada `event`:

```text
preciseStart = 720720 + measure.start_units + event.offset_units
```

Exemplo:

```xml
<TGBeat>
  <preciseStart>720720</preciseStart>
  <voice>
    <duration value="4"/>
    <note value="1" velocity="90" string="2"/>
  </voice>
  <voice empty="true">
    <duration value="4"/>
  </voice>
</TGBeat>
```

### Duration -> duration

Contrato:

```json
{
  "value": 8,
  "dots": 1,
  "tuplet": { "enters": 1, "times": 1 },
  "units": 540540
}
```

XML:

```xml
<duration value="8" dotted="dotted"/>
```

Contrato:

```json
{
  "value": 8,
  "dots": 0,
  "tuplet": { "enters": 3, "times": 2 },
  "units": 240240
}
```

XML:

```xml
<duration value="8">
  <divisionType enters="3" times="2"/>
</duration>
```

### Note -> note

Contrato:

```json
{
  "pitch_midi": 60,
  "string": 2,
  "fret": 1,
  "velocity": 90,
  "tied": false,
  "effects": []
}
```

XML:

```xml
<note value="1" velocity="90" string="2"/>
```

Regra:

- `note.value` no XML recebe `fret`.
- `note.string` no XML recebe `string`.
- `pitch_midi` nao e escrito diretamente no XML de nota; ele serve para validacao.

## Responsabilidades da camada 2

A camada 2 deve entregar:

1. BPM ou mapa de tempo.
2. Formula de compasso.
3. Eventos separados por track.
4. Notas quantizadas.
5. Pausas explicitas.
6. Notas divididas quando atravessam compasso.
7. Ligaduras marcadas com `tied`.
8. Posicao de tablatura para tracks `fretted-string`.
9. Confianca e rastreabilidade quando disponivel.

Se a camada 2 ainda so tiver `pitch_midi`, `onset_seconds` e `offset_seconds`, o contrato ainda nao esta pronto. Antes de chamar a camada 3, precisa passar por:

```text
raw note events
  -> tempo alignment
  -> quantization
  -> measure splitting
  -> rest insertion
  -> tab assignment
  -> MelodyScoreContract
```

## Responsabilidades da camada 3

A camada 3 deve:

1. Validar o contrato.
2. Criar canais General MIDI.
3. Criar headers de compasso.
4. Criar tracks, strings e measures.
5. Converter events em beats.
6. Converter notes em `string/fret`.
7. Escrever `content.xml`.
8. Escrever `version.txt`.
9. Empacotar `.tg`.

A camada 3 pode rejeitar o contrato com erro claro. Ela nao deve tentar consertar musicalmente o documento.

## Regras de validacao obrigatorias

### Estrutura

- `contract.name == "MelodyScoreContract"`.
- `contract.version` deve ser compativel com o writer.
- `project.units_per_quarter == 720720`.
- Deve existir pelo menos uma track.
- Deve existir pelo menos um compasso.

### Tempo e compasso

- `tempo_map` deve ter uma entrada iniciando no compasso `1`.
- `time_signatures` deve ter uma entrada iniciando no compasso `1`.
- `bpm > 0`.
- `numerator > 0`.
- `denominator` deve ser `1`, `2`, `4`, `8`, `16`, `32` ou `64`.

### Tracks

- `track.id` deve ser unico.
- `track.kind` deve ser `fretted-string` no v0.1.0.
- `tuning` nao pode ter cordas duplicadas.
- `max_fret >= 0`.
- Cada track deve ter o mesmo numero de compassos globais.

### Measures

- `measure.number` deve ser sequencial.
- `measure.start_units` deve ser sequencial e consistente com compassos anteriores.
- `measure.duration_units` deve bater com a formula de compasso ativa.
- `events` deve cobrir exatamente `duration_units`.

### Events

- `offset_units >= 0`.
- `offset_units + duration.units <= measure.duration_units`.
- Eventos devem estar ordenados por `offset_units`.
- Eventos nao podem se sobrepor.
- Nao pode haver buraco entre eventos; pausas devem ser explicitas.
- `duration.units` deve bater com `duration.value`, `dots` e `tuplet`.

### Notes

- `pitch_midi` deve estar entre `0` e `127`.
- `string` deve existir na afinacao da track.
- `fret` deve estar entre `0` e `track.max_fret`.
- `velocity` deve estar entre `1` e `127`.
- Para `fretted-string`, `pitch_midi == tuning[string].pitch_midi + fret`.
- Em um acorde, duas notas nao devem usar a mesma corda no mesmo evento.

## Erros recomendados

O validador deve retornar erros com codigo, caminho e mensagem.

Exemplo:

```json
{
  "code": "TAB_PITCH_MISMATCH",
  "path": "tracks[0].measures[0].events[2].notes[0]",
  "message": "pitch_midi 64 does not match string 2 fret 3; expected 62"
}
```

Codigos iniciais:

- `UNSUPPORTED_CONTRACT_VERSION`
- `INVALID_UNITS_PER_QUARTER`
- `MISSING_TEMPO`
- `MISSING_TIME_SIGNATURE`
- `INVALID_MEASURE_DURATION`
- `EVENT_GAP`
- `EVENT_OVERLAP`
- `DURATION_NOTATION_MISMATCH`
- `INVALID_STRING`
- `INVALID_FRET`
- `TAB_PITCH_MISMATCH`
- `DUPLICATE_STRING_IN_CHORD`
- `UNSUPPORTED_EFFECT`

## Dados de confianca e rastreabilidade

`confidence` e `source` nao devem alterar o XML no MVP, mas sao importantes para debug e UX.

Exemplo:

```json
{
  "confidence": {
    "overall": 0.71,
    "pitch": 0.92,
    "onset": 0.76,
    "duration": 0.55,
    "tab_position": 0.80
  },
  "source": {
    "stem_id": "guitar_1",
    "source_model": "basic-pitch",
    "onset_seconds": 3.214,
    "offset_seconds": 3.702,
    "raw_pitch_midi": 64.1
  }
}
```

Uso esperado:

- destacar notas incertas em uma UI futura;
- comparar resultado antes/depois da quantizacao;
- auditar erros do modelo;
- reprocessar apenas trechos problematicos.

## Contrato vs formatos externos

Este contrato nao e MIDI, MusicXML nem `.tg`.

Ele existe para ser:

- mais rigido que eventos MIDI crus;
- mais simples que o XML completo do TuxGuitar;
- independente de detalhes de ZIP/XML;
- suficiente para gerar tablatura tocavel.

MIDI pode ser usado como entrada intermediaria para a camada 2, mas nao deve ser a fronteira final com a camada 3 porque nao contem string/fret nem notacao de pausas/compassos de forma confiavel.

## Checklist para chamar o writer .tg

Antes de chamar a camada 3, a camada 2 deve conseguir responder `sim` para todos:

- Todas as notas tem `pitch_midi`?
- Todas as notas de guitarra/baixo tem `string` e `fret`?
- Todas as notas foram quantizadas?
- Todas as duracoes tem `value`, `dots`, `tuplet` e `units`?
- Todos os compassos tem duracao correta?
- As pausas foram inseridas explicitamente?
- Notas cruzando compassos foram quebradas e ligadas?
- O documento passou no validador?

Se qualquer resposta for `nao`, ainda nao e entrada valida para a camada 3.

## Evolucao prevista

### v0.2

- multiplas vozes por track;
- drums/percussion;
- efeitos estruturados basicos: bend, harmonic, grace, trill;
- markers e sections;
- suporte melhor a tempo map.

### v0.3

- dedilhado;
- informacao de posicao de mao;
- alternativas de tablatura por nota;
- score confidence por compasso;
- anotacoes de revisao humana.

### v1.0

- schema JSON formal;
- suite de validacao;
- exemplos golden;
- round-trip test com TuxGuitar.
