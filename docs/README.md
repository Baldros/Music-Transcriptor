# Pesquisa de Viabilidade - Audio para TuxGuitar

Data da pesquisa: 2026-06-25.

Objetivo do projeto: receber uma musica em audio, extrair informacao musical e gerar um arquivo `.tg` nativo do TuxGuitar.

## Conclusao curta

E viavel construir um sistema util, mas nao e viavel esperar uma transcricao perfeita de uma musica completa arbitraria em uma primeira versao.

O pipeline end-to-end tem tres problemas independentes e dificeis:

1. Separar instrumentos de uma mistura finalizada.
2. Converter audio separado em eventos musicais: notas, ritmo, duracao, instrumento, tecnica e, para guitarra, string/fret.
3. Escrever um arquivo `.tg` correto.

O ponto 3 parece o mais controlavel: o TuxGuitar atual usa `.tg` como um arquivo ZIP com `version.txt` e `content.xml`, e o schema pode ser inferido do codigo Java oficial. Os pontos 1 e 2 continuam sendo pesquisa aplicada, com qualidade muito dependente do genero, mixagem e instrumento.

## Arquivos

- [01-source-separation.md](01-source-separation.md): separacao de instrumentos e stems.
- [02-audio-to-notes-transcription.md](02-audio-to-notes-transcription.md): transcricao audio -> notas/MIDI/tablatura.
- [03-tuxguitar-tg-output.md](03-tuxguitar-tg-output.md): escrita do formato `.tg`.
- [04-architecture-and-roadmap.md](04-architecture-and-roadmap.md): arquitetura proposta, MVP e experimentos.
- [05-layer2-layer3-melody-contract.md](05-layer2-layer3-melody-contract.md): contrato rigido entre dados musicais simbolicos e writer `.tg`.
- [06-audio-to-contract-mvp.md](06-audio-to-contract-mvp.md): primeiro MVP de audio monofonico para contrato.

## Decisoes iniciais recomendadas

- Comecar com entrada de audio de um unico instrumento ou stem ja separado.
- Usar MIDI/eventos internos como representacao intermediaria.
- Gerar `.tg` diretamente no formato moderno do TuxGuitar 2.0, em vez de tentar escrever o antigo binario 1.x.
- Para musica completa, testar primeiro `Demucs`/`audio-separator`/APIs comerciais e medir qualidade antes de prometer separacao fina de guitarras.
- Tratar "guitarra base vs guitarra solo" como uma fase avancada: isso e separacao monotimbral, muito mais dificil que separar vocal/bateria/baixo/outros.

## Fontes principais

- TuxGuitar docs: https://www.tuxguitar.app/files/devel/desktop/help/file_formats.html
- TuxGuitar source: https://github.com/helge17/tuxguitar
- TuxGuitar format discussion: https://github.com/helge17/tuxguitar/discussions/264
- Demucs: https://github.com/facebookresearch/demucs
- Spleeter: https://github.com/deezer/spleeter
- Open-Unmix: https://sigsep.github.io/open-unmix/
- Basic Pitch: https://github.com/spotify/basic-pitch
- MT3: https://github.com/magenta/mt3
- Omnizart: https://github.com/Music-and-Culture-Technology-Lab/omnizart
