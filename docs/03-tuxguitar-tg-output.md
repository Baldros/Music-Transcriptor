# 03 - Escrita de Arquivo .tg do TuxGuitar

## Conclusao

Gerar `.tg` e viavel.

O formato antigo do TuxGuitar 1.x era binario e nao documentado. O formato atual no branch master do TuxGuitar e identificado como `TuxGuitar 2.0` e e um arquivo ZIP contendo:

- `version.txt`
- `content.xml`

Isso torna a escrita direta muito mais simples que engenharia reversa binaria.

## Fontes

- Ajuda oficial de formatos: https://www.tuxguitar.app/files/devel/desktop/help/file_formats.html
- Repositorio oficial atual: https://github.com/helge17/tuxguitar
- Discussao sobre documentacao do `.tg`: https://github.com/helge17/tuxguitar/discussions/264
- Codigo relevante no repo:
  - `common/TuxGuitar-lib/src/main/java/app/tuxguitar/io/tg/TGStream.java`
  - `common/TuxGuitar-lib/src/main/java/app/tuxguitar/io/tg/TGSongWriterImpl.java`
  - `common/TuxGuitar-lib/src/main/java/app/tuxguitar/io/tg/TGSongReaderImpl.java`
  - `common/TuxGuitar-compat/src/main/java/app/tuxguitar/io/tg/v15/TGSongWriterImpl.java`

## O que a documentacao oficial diz

A ajuda oficial confirma que `.tg` e o formato proprio do TuxGuitar e recomenda salvar no formato nativo mais recente. Tambem informa que TuxGuitar abre/importa varios formatos como Guitar Pro, PowerTab, TablEdit e MIDI, e exporta MIDI, MusicXML, LilyPond, PDF, SVG etc.

Ponto importante: a ajuda alerta que importacao MIDI e apenas conveniencia; TuxGuitar e editor de tablatura, nao editor MIDI. Em particular, MIDI nao contem string/fret, e a atribuicao para tablatura e arbitraria e costuma exigir ajuste manual.

## Estado do formato .tg

### Antigo 1.x

A discussao oficial no GitHub registrou que o formato antigo era proprietario, binario e nao documentado. O caminho correto era seguir o codigo Java de reader/writer.

No codigo atual, a compatibilidade antiga fica em:

`common/TuxGuitar-compat/src/main/java/app/tuxguitar/io/tg/v15/`

O writer v1.5 usa `DataOutputStream` e grava campos manualmente em binario.

### Atual 2.0

No `master` atual, `TGStream.java` define:

- `FILE_FORMAT_TGVERSION = new TGVersion(2,0,0)`
- `TG_FORMAT = new TGFileFormat("TuxGuitar 2.0", "application/x-tuxguitar", ["tg"])`
- `CONTENT_FILE_NAME = "content.xml"`
- `VERSION_FILE_NAME = "version.txt"`
- `VERSION_PREFIX = "TuxGuitar_file_format"`

O writer cria um ZIP e adiciona:

- `version.txt` com conteudo no formato `TuxGuitar_file_format 2.0.0`
- `content.xml` com o DOM XML da musica

O reader abre o ZIP, le a versao e depois parseia o `content.xml`.

## Estrutura XML minima

Um arquivo de teste no repo mostra a estrutura base:

```xml
<TuxGuitarFile>
  <TGVersion major="1" minor="6" revision="6"/>
  <TGSong>
    <name/>
    <artist/>
    <album/>
    <author/>
    <date/>
    <copyright/>
    <writer/>
    <transcriber/>
    <comments/>
    <TGChannel>...</TGChannel>
    <TGMeasureHeader>...</TGMeasureHeader>
    <TGTrack maxFret="29">...</TGTrack>
  </TGSong>
</TuxGuitarFile>
```

Campos principais:

- `TGChannel`: id, bank, program, volume, balance, chorus, reverb, phaser, tremolo, name.
- `TGMeasureHeader`: timeSignature, tempo, repeats, markers, tripletFeel, lineBreak.
- `TGTrack`: name, channelId, color, strings, lyric, measures.
- `TGMeasure`: clef, keySignature, beats.
- `TGBeat`: preciseStart, stroke, pickStroke, chord, text, voices.
- `voice`: duration, notes.
- `note`: value/fret, string, velocity, tiedNote e efeitos.

## Relacao com MIDI e MusicXML

TuxGuitar consegue importar MIDI e exportar MusicXML, mas para o nosso projeto existem tres opcoes:

### Opcao A - Gerar MIDI e importar no TuxGuitar

Vantagem:

- Mais facil no inicio.
- Podemos usar `pretty_midi`, `mido` ou Basic Pitch direto.

Desvantagem:

- MIDI nao guarda tablatura.
- TuxGuitar vai escolher string/fret com heuristicas.
- Pode gerar ritmos estranhos se o MIDI nao estiver quantizado.
- Nao gera `.tg` automaticamente sem uma etapa extra.

### Opcao B - Gerar GP3/GP4/GP5 com PyGuitarPro

Vantagem:

- PyGuitarPro escreve formatos Guitar Pro 3/4/5.
- TuxGuitar abre/exporta esses formatos.
- GP e mais proximo de tablatura que MIDI.

Desvantagem:

- Ainda nao e `.tg`.
- Formatos Guitar Pro antigos podem perder informacao.
- Precisaria converter para `.tg` depois.

### Opcao C - Gerar `.tg` 2.0 diretamente

Vantagem:

- Atende exatamente ao objetivo.
- Formato atual e ZIP/XML.
- Evita depender de UI ou conversor externo.
- Permite controlar tracks, strings, frets e duracoes.

Desvantagem:

- Precisamos implementar o schema suficiente e testar no TuxGuitar.
- O schema e inferido do codigo, nao de especificacao formal.
- Precisa manter compatibilidade com mudancas futuras.

Recomendacao: Opcao C para o produto; Opcao A para debug/MVP intermediario.

## Como escrever .tg diretamente

1. Criar `content.xml` com raiz `TuxGuitarFile`.
2. Adicionar `TGVersion` com versao do app/gerador. O writer oficial usa `TGVersion.CURRENT`, nao a versao do formato.
3. Adicionar `TGSong`.
4. Criar canais General MIDI.
5. Criar measure headers com tempo e time signature.
6. Criar tracks com afinacao:
   - guitarra padrao: E2 A2 D3 G3 B3 E4 = MIDI 40, 45, 50, 55, 59, 64;
   - baixo padrao: E1 A1 D2 G2 = MIDI 28, 33, 38, 43.
7. Criar measures, beats, voices, durations e notes.
8. Compactar ZIP com `version.txt` e `content.xml`.
9. Salvar com extensao `.tg`.
10. Abrir no TuxGuitar e validar round-trip.

## Pontos de cuidado

### Duracao e tempo interno

TuxGuitar usa constantes internas como `TGDuration.QUARTER_TIME = 960` e tambem `WHOLE_PRECISE_DURATION` para evitar erros de tuplet/dotted notes. O XML usa `preciseStart` e `duration`.

Nao devemos inventar uma escala de ticks sem alinhar com o codigo. A implementacao deve copiar a logica de duracoes do TuxGuitar ou usar uma camada Java do proprio TuxGuitar para criar o objeto `TGSong`.

### Compatibilidade

O reader aceita major version igual ao formato atual. Se o major for maior, rejeita. Minor maior marca `newerFileFormatDetected`. Portanto, nossos arquivos devem escrever `version.txt` com `2.0.0` enquanto miramos essa versao.

### XML seguro

O reader oficial desabilita DOCTYPE para evitar XXE. Nosso writer nao precisa de DOCTYPE.

### Efeitos de guitarra

O formato suporta varios efeitos:

- vibrato;
- deadNote;
- slide;
- hammer;
- ghostNote;
- palmMute;
- bend;
- tremoloBar;
- harmonic;
- grace;
- trill;
- tremoloPicking;
- pickStroke.

Para MVP, melhor ignorar efeitos e gerar notas limpas. Depois podemos inferir tecnicas.

## Plano de implementacao recomendado

1. Implementar um `tg_writer` pequeno em Python que gere um arquivo `.tg` com:
   - uma track;
   - afinacao padrao;
   - compasso 4/4;
   - tempo fixo;
   - algumas notas simples.
2. Validar abrindo no TuxGuitar.
3. Criar teste automatizado que abre o `.tg` como ZIP e valida:
   - `version.txt`;
   - XML bem formado;
   - presenca de canais, measure headers e tracks.
4. Depois comparar com TuxGuitar:
   - gerar `.tg`;
   - abrir e salvar novamente no TuxGuitar;
   - descompactar ambos e comparar estrutura.
5. So depois conectar a transcricao real.

## Perguntas em aberto

- O usuario alvo tera TuxGuitar 2.x instalado? Se precisarmos suportar TuxGuitar 1.5, o writer binario antigo e muito mais trabalhoso.
- Vamos representar bateria/percussao em tablatura ou como track MIDI/percussion?
- Queremos preservar pitch bends do Basic Pitch como bends de guitarra ou ignorar no MVP?
- Vamos usar MusicXML/GP5 como formato de debug?

## Consultas em ingles usadas

- `TuxGuitar .tg file format writer source code`
- `TuxGuitar file format .tg documentation`
- `Documentation tg file format helge17 tuxguitar discussion`
- `pyguitarpro Python library Guitar Pro file write official GitHub`
