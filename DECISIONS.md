# DECISIONS.md — ThisReelOrThat

Registro do que está no ar, do que foi rejeitado e por quê. Escrito para ser lido em três meses por alguém que não viveu as decisões — incluindo você mesmo.

Convenção: **ATIVO** roda em produção. **REJEITADO** foi testado e reprovado. **PENDENTE** está na fila. Cada rejeição diz o que mediu e por que caiu, porque a lição está aí.

---

## 1. Configuração ativa

| componente | valor |
|---|---|
| Pool de pares | `old_pool_v2` (estratificado, quota por eixo) |
| Gate de sonda cega | **desligado** |
| Variedade | banda de 3% + hash de sessão |
| Geometria | `reality-split v3` (12 eixos) |
| Blocklist de probes | ativa (aplicada antes do cálculo de contraste) |
| Rerank semântico | `text-embedding-3-small` + `endorsed_minus_none` + janela 60 — **evidência fraca, ver §5** |
| Clusters | K = 80, mediana 15 filmes, piso `exp(H)` = 16,67 |

Catálogos: 282 probes (assistidos, incluindo séries) · 1.215 candidatos (não assistidos).

Contextos privados adicionais (listas pessoais) rodam fora do repositório — ver §10.

---

## 2. Rotulagem — a camada que mais importou

**A auditoria de rótulos foi a única intervenção com efeito grande e replicado: mediana da suíte de 30 → 7.** Todas as tentativas de melhorar o motor por mecanismo falharam; melhorar os dados funcionou.

ATIVO:

- **12 eixos.** Os 11 originais + a divisão de `realistic_fantastic` em `literal_impossibility` (o mundo contém algo impossível?) e `subjective_unreality` (a narração é confiável?). Correlação entre os dois: r = 0,154 — dimensões independentes.
- **3 passadas por filme, mediana por eixo.** Confiança = discordância entre passadas.
- **Fatos vêm do TMDB, não do LLM:** idioma, animação, ano. Erros como *Pan's Labyrinth* rotulado anglófono são falha de recall, não de julgamento.
- **Ancoragem em texto:** sinopse + review, não memória paramétrica.
- **15 controles re-inferidos em todo lote.** Gates: deriva média > 0,08 ou eixo único > 0,15 reprova o lote.
- **Gate de correlação para eixo novo:** |r| ≥ 0,85 contra dimensão de probing existente → o eixo fica como label de matching e nunca ganha pergunta.
- **Pesos:** idioma **0**, animação **0,2**, resto cheio. Motivo em §4.
- **Fusão peso↔catarse apenas no probing;** separados no matching, porque a variância residual é real (*Life Is Beautiful*, *Seven Samurai*: pesados no conteúdo, catárticos na resolução).

O campo de confiança auto-reportado da rotulagem antiga era **vacuoso**: média 0,939, e todos os erros encontrados tinham confiança 0,96–0,99. Discordância entre passadas é o único sinal de confiança que funciona.

---

## 3. Quiz — respostas, parada, entrega

ATIVO:

- **Quatro respostas:** A, B, "qualquer um serve", "nenhum me atrai". Nada além disso.
- **Likelihood:** κ = 3,5 · teto de evidência 1,25 · σ_tie 0,55 · força do "nenhum" 2,0 / bias 0,15.
- **Reponderação suave, nunca eliminação dura.**
- **Coarse até localizar** (top-1 ≥ 0,45 ou top-3 ≥ 0,70 com consistência afirmativa), depois fine intra-região (`legível E ambos na região`).
- **Mínimo 5 rodadas, teto 10 + min(nenhum, 4).**
- **Parada:** top-3 ≥ 0,75 e `exp(H)/piso ≤ 2,0`. ⚠️ Em validação sintética de escala real, a parada disparou em 3 de 50 sessões — 94% bateram o teto. Ver §6.
- **Guarda de evidência afirmativa:** pick simples exige ≥3 respostas A/B e A/B ≥ "nenhum"; caso contrário sai pick duplo por polos com baixa confiança.
- **Entrega: um pick, não shortlist.** `argmax` do posterior após máscara de elegibilidade, dedupe de franquia e rerank semântico. Botões `[me dá outro]` e `[vou assistir]`.
  - `me dá outro` anda na ordem ranqueada (2º, 3º, 4º...) sem recalcular posterior nem mudar de região. Cada toque é logado como **rejeição explícita** daquele filme, com a posição — é o único canal de item que o sistema tem.
  - Após ~5-6 recusas o card avisa que a confiança caiu. Não bloqueia.
  - `vou assistir` marca aceitação real. Sem esse toque nada conta como aceito — o quiz também é usado pra testar e pra demonstrar.
  - A ordem ranqueada é **íntegra**: diversidade de cluster nunca desaloja candidato de alta confiança.
- **Elegibilidade é máscara ANTES do ranqueamento.** Nunca filtro depois. Isso morde duas vezes na história do projeto (duração e disponibilidade).
- **Identidade por TMDB.** Serviços de match por título entram só como enriquecimento pós-pick; falha de match nunca exclui candidato.
- **Dois canais de feedback, deliberadamente separados.** `vibe` (👍/👎: "era a vibe que eu esperava?") avalia o **motor**. Nota/review no Letterboxd avalia o **filme**. Misturar os dois ensina errado — filme ótimo entregue na noite errada levaria 👍.
- **Lembrete de log:** ao aceitar um pick, agenda um lembrete único para duração + 30 min, com botão `[já loguei]`. Review mandado na conversa é gatilho suficiente.
- **Gosto estável como mistura de 2 clusters.** Média de vetores perde até para prior uniforme quando o gosto é bimodal (−7,17 vs −7,10 vs −5,22 em log-prob).

---

### Regra de escopo do quiz

**A tela do quiz é só isso-ou-aquilo.** Um par, quatro botões, repete até a parada. Nada além disso entra: nem palpite corrigível, nem chips de direção, nem legenda de eixo, nem quinta resposta. Qualquer elemento que peça raciocínio explícito sobre atributos quebra a premissa de ler vontade do subconsciente, e já está vetado por princípio.

Única exceção: a **pergunta de duração** no início. É contexto declarado, não mood. E é **teto**, não faixa — "tenho 150 minutos" significa qualquer filme até 150.

### Métrica de produto

**Posição do pick aceito.** Por sessão, em que posição do ranking estava o filme aceito com `vou assistir` (1 = acertou de primeira). É avaliação de ranqueamento com ground truth real, saindo do uso normal, sem protocolo.

`SC@3` (célula certa no top-3) foi a métrica durante a fase de validação sintética e **deixou de ser métrica de produto** quando a entrega virou pick único.

---

## 4. Achados que sustentam o desenho

**"Nenhum" protege o posterior — efeito mais forte medido no projeto.** Braço `forced_choice` (n=50): mediana de posição 45 e média 77, contra 31,5 e 40 do baseline. Mecanismo: quando o par é ruim, escolher à força injeta direção confundida; recusar apenas suprime. Corroborado em sessões humanas (0 "nenhum" → 252º; 3 "nenhum" → pick nº 1).

**Flags binárias não são eixos de mood.** 99,7% dos filmes ficam em \|v\|>0,8 em animação e 99,1% em idioma (bimodalidade de Sarle 0,995 e 0,993). Um par misto contrasta 2,96σ em idioma contra 1,0–1,4σ dos eixos reais — a flag sempre domina. Pior: com os 12 eixos crus, **100% dos clusters eram >90% puros em idioma** e nenhum cluster tinha mood atravessando animação. Os clusters eram ~9 células de mood repetidas em 4 quadrantes, e um crédito espúrio trancava o posterior no quadrante errado.

**Pureza de eixo é impossível no bloco de tom.** `heavy_light × gray_cathartic` = +0,90; heavy × demanding = +0,78; gray × demanding = +0,76; heavy × comic = −0,72. Filme que difere em peso também difere em catarse — é estrutura do cinema, não lacuna de catálogo. Exigir pureza reprova sempre nesses eixos (7 a 11 pares puros em ~80 mil).

**O crédito por rodada é descorrelacionado da razão da escolha.** Concordância entre motivo declarado e eixo creditado: 9,5%, com baseline aleatório de 10,3% (n=1.952 rodadas). Isso é o teto do formato e explica as oito refutações de §5 de uma vez: não há sinal de razão para recuperar.

**Cobertura tem que ser objetivo, não piso.** O invariante exigia ≥32 pares por eixo; o otimizador cumpriu o mínimo e gastou o resto do pool em outra coisa. Resultado: 8 de 10 eixos perderam cobertura do v2 pro v3 (`subjective_unreality` 226 → 45). Foi por isso que o pool "melhorado" piorou o motor.

---

## 5. Transporte — a lição mais transferível do projeto

Durante semanas a premissa foi "zero inferência de IA no quiz". Ela valia pro motor e era **falsa pro transporte**.

Medição de uma rodada real, do toque no botão até a próxima pergunta na tela: **179,2 segundos**.

| etapa | tempo |
|---|---:|
| callback → agente desperto | ~34,4 s |
| agente desperto → handler começar | ~16,1 s |
| leitura de estado e comandos auxiliares | ~1,9 s |
| **seleção do par** | **28,6 ms** |
| **preparação de mídia** | **63,7 ms** |
| API do Telegram | 1,73 s |
| LLM/orquestração entre comandos | ~141 s |

**O motor é 0,05% da espera.** 92 ms de 179.200 ms. Os outros 99,95% eram o agente acordando, lendo skill, procurando perfil, consultando `--help` e decidindo o que executar — a cada toque de botão.

Todo o trabalho de otimização feito antes disso (prefetch especulativo das 4 respostas, vetorização do EIG, orçamento de 300 ms na seleção do par) melhorou um componente **três ordens de magnitude menor** que o gargalo real.

**Nenhuma das 850 sessões sintéticas podia achar isso**, porque nelas não existe Telegram nem agente. Foi achado em uma sessão de uso.

### Arquitetura correta

`callback do Telegram → serviço residente → estado em memória → likelihood/seleção → imagem em disco → Telegram`

- **Processo residente** (systemd user service): carrega o runtime uma vez no startup, mantém em memória, persiste estado a cada resposta.
- **Bot dedicado** só pro quiz, isolando o raio de falha da mensageria principal.
- **Zero LLM por rodada.** O agente entra em duas pontas apenas: warming (offline) e card final se houver pedido de análise.
- **Cache permanente dos pôsteres dos probes.** Os pares só usam os assistidos, sempre os mesmos filmes — baixa uma vez, nunca mais busca em runtime.
- **Pré-composição com `file_id`.** As imagens "A vs B" de cada par do pool são compostas e enviadas uma vez; o Telegram devolve um `file_id` reutilizável. Depois disso enviar uma rodada é uma chamada com um ID, sem upload. Invalidado por hash do runtime ou troca de bot.

Critério de aceite: p50 < 500 ms do toque até a pergunta na tela, p99 < 2 s.

**Lição geral: meça o caminho ponta a ponta antes de otimizar qualquer componente.** Perfil de CPU do algoritmo não vê o gargalo se ele mora no transporte.

---

## 6. Rejeitados

### Vetados pelo dono do produto (não voltam)

Conjuntos de 3 filmes por lado · legenda de eixo no par · tríades · perguntas de rejeição ("qual você NÃO quer") · quinta resposta ("não lembro desses") · **palpite corrigível** · **shortlist de 3**.

Notas sobre os dois últimos: o **palpite corrigível** ("tá parecendo noite de X — é isso?" com atalhos de direção) chegou a ser implementado e foi **removido do runtime**, não apenas desativado. Ele disparava após 6 rodadas sem localizar e substituía a rodada — mas os botões eram vocabulário de rubrica com outro nome ("mais acelerado" = `slow_propulsive`), exatamente o que a legenda de eixo tinha de errado. A **shortlist de 3** foi proposta do lado de design, nunca pedido do produto; virou pick único.

Razão comum: o quiz existe para ler vontade do subconsciente. Nomear o eixo ou pedir raciocínio explícito empurra para o modo consciente e destrói a premissa.

### Refutados por teste

| ideia | o que mediu | resultado |
|---|---|---|
| Árvore de decisão pré-computada | latência | seleção local é sub-milissegundo; congelaria política não calibrada |
| Pureza no update | acerto na persona "razão confundida" | 57,4% → 57,4% |
| Corroboração leave-one-out | fragilidade da parada | marcou 100% das sessões como frágeis — a régua media a si mesma |
| Atribuição mascarada | deriva de eixo | piorou: −1,420 → −1,594 |
| Bônus de endosso RBF | posição do alvo | fraco e instável em todos os β |
| Whitening / Mahalanobis | acerto agregado | Demon Slayer 1 → 37; melhorou 4, piorou 5 |
| Eixo congelado por região | posição do alvo | Dark Knight 164 → 229 |
| Atenuação de crédito incidental | curva 1,0/0,5/0,3/0,0 | monótona piorando — crédito incidental é ruidoso mas útil |
| Catraca do termo `att` em A/B | posição do alvo | 178 → 178 |
| Janela semântica por `exp(H)` | lift por múltiplo | lift pequeno em toda a faixa; unidade errada |
| Cobertura entre catálogos | distância probe↔candidato | 0 de 1.215 candidatos além de 1σ; distância não prevê falha |
| Filtro intra-célula universal | "nenhum" intra vs cross | 33,8% vs 22,2%, pegou 3 de 4 casos — sinal fraco |
| Fine só no fechamento | acerto exato | 44% contra 64% do fine intercalado |

### Sob suspeita, ativo por ora

**Rerank semântico.** Promovido com base em 500 sessões que tinham **vazamento**: em 103 delas o alvo aparecia como probe e podia ser endossado — canal que produção não tem. Nas 397 sessões limpas, top-30 cai de 47,0% para 38,3%, apenas 1,05x o aleatório pareado, e alvo@3 fica indistinguível de aleatório. Em escala de produção dá 2,34x, mas isso são 4 sessões contra 2, e alvo@3 vai de 4% para **0%** — a camada acerta mais a célula e afunda o filme exato, que é o viés de familiaridade previsto.

Gatilho de desativação: o primeiro sinal real de recomendações previsíveis ou "mais do mesmo" no uso.

---

## 7. Limitações conhecidas

**Resolução do instrumento: ~top 10%.** Medido cinco vezes de forma independente. Com 282 candidatos, o alvo aterrissa consistentemente entre a 16ª e a 39ª posição. Isso é piso de entropia, não falta de calibração: filmes com vetores quase idênticos são indistinguíveis por qualquer sequência de respostas. **Perseguir top-1 é perda de tempo** — o produto entrega célula de mood, não filme exato.

**Validação em escala de produção é ruim.** Posterior faz 1,17x aleatório com K=80; gosto estável **sem quiz** faz 1,76x. As diferenças são de uma ou duas sessões em N=50, então nada é conclusivo — mas o quiz não demonstrou pagar o próprio custo de interação em escala real.

**Ressalva sobre esse resultado:** em produção **não existe alvo**. Todo o framework mediu recuperação de um filme específico escondido; o produto entrega três filmes para uma vontade difusa. O 1,17x pode ser falha real ou métrica errada, e nenhum teste offline distingue as duas.

**Parada quase nunca dispara em escala real.** 47 de 50 sessões bateram o teto com K=80. Nenhum limiar testado resolveu (K=43 deu 92% de teto). O gate de confiança raramente morde.

**SC@3 não é comparável entre catálogos.** Depende do número de clusters: aleatório dá 30,5% no NYT (9 clusters), 40,6% no target-test (~18) e 3,41% em produção (80). Métrica oficial passa a ser **razão sobre aleatório** e **lift normalizado** `(obs − rand)/(1 − rand)`. Todo número absoluto histórico comparado entre contextos está inválido.

**O simulador não mede legibilidade.** As personas respondem pela mesma likelihood do motor, então uma sonda cega produz resposta auto-consistente e não reproduz o envenenamento humano por escolha forçada. Nenhum dos 10 braços da campanha sabe que existe pergunta irrespondível — o respondente automático aperta "nenhum" e segue; o humano abandona a sessão.

**Calibração do respondente automático: 75,4%.** Valida comparação entre braços (viés constante se cancela), não números absolutos. Uma em quatro respostas difere do humano, ~3 por sessão.

**Regiões singleton.** O catálogo tem gêneros com n≈1 (documentário: praticamente só *Jiro Dreams of Sushi*). Inferência nessas regiões é sem sentido — "mesma célula" não existe com um filme.

---

## 8. Pendente

1. **Cobertura como objetivo na função de build do pool** (não como piso de 32). Dormente: o v2 ativo já tem cobertura boa; só importa se alguém reconstruir o pool.
2. **Auditoria manual dos rótulos** — 7 filmes de confiança baixa remanescentes (3 em `gray_cathartic`) + 2 eixos divergentes de *Funeral Parade of Roses* (`slow_propulsive`, `classic_contemporary`).
3. **Revisão de rubrica de `gray_cathartic`** — 3 de 7 casos incertos concentrados nele.
4. **Serviço residente** — núcleo construído, aguardando token do bot dedicado, warming dos `file_id` e medição real de p50/p99. Até então o transporte segue passando pelo agente.
5. **Bug aberto: piso de entropia obsoleto sob máscara.** O piso é calculado no build do catálogo cheio, mas as máscaras (duração, disponibilidade, blocklist) encolhem o conjunto elegível sem atualizar o piso. Como a parada divide por ele, ela dispara **prematuramente** em qualquer sessão com filtro. O fix é recalcular piso e δ no início da sessão sobre o conjunto elegível real. Não medido, não corrigido — sintoma observável: parar em 5-6 rodadas e entregar pick ruim.
6. **Logging automático no Letterboxd** — o Letterboxd não tem API pública de escrita. Caminho ainda não definido (automação de navegador ou import CSV). Até então, lembrete com botão `[já loguei]` e log manual.
7. **Feedback de vibe e posição do pick aceito** — acumulando com o uso. São as duas únicas fontes de verdade que existem; nenhuma análise offline substitui.

---

## 9. Lição de método

Oito hipóteses de mecanismo foram refutadas por ablação. A única intervenção com efeito grande e replicado veio de **verificação empírica direta** — auditar 12 filmes conhecidos na mão e achar 4 rótulos indefensáveis.

Narrativa causal convincente não sobreviveu ao teste; conferir os dados sobreviveu.

E o instrumento que achou mais bugs reais não foi o simulador de 500 sessões — foram sessões humanas isoladas. A sessão com 64% de "nenhum" gerou a reconstrução do pool. O 252º de *Sound of Metal* gerou o gate de sonda cega. Uma reação de "esse filme não tem nada a ver" identificou um caso que os vetores confirmaram depois.

---

## 10. Contextos múltiplos — restringir a um catálogo específico

O motor é agnóstico de catálogo: o posterior roda sobre qualquer conjunto de candidatos rotulado, e os probes continuam sendo os assistidos. Isso permite criar um **contexto** que responde apenas dentro de uma lista escolhida — uma lista de melhores do ano, uma seleção de festival, filmes de um diretor, o que for.

No repositório entra o **mecanismo**, não listas específicas. Quem usa cria os próprios contextos via agente/pipeline.

O que um contexto novo exige (nada disso transfere do contexto principal):

1. **Rotulagem dos filmes da lista** na rubrica atual — 12 eixos, 3 passadas, mesmos controles, fatos vindos do TMDB. Filmes já presentes no catálogo principal reaproveitam o rótulo.
2. **Runtime próprio:** candidatos reestandardizados, K próprio, piso `exp(H)` e δ próprios.
3. **Limiares de parada recalibrados.** Isto é o que mais quebra: catálogo pequeno é regime completamente diferente.
4. **Validação antes de publicar**, com dois baselines obrigatórios.

### Três armadilhas medidas na prática

**Limiar impossível.** Um critério de parada expresso como número absoluto de candidatos efetivos pode ficar **abaixo do piso de entropia** do catálogo — e aí nunca dispara. Aconteceu: piso 7,03 com limiar de 4,0. Sintomas: 40% das sessões no teto, e um sweep de sete valores de limiar retornando resultado idêntico em todas as linhas. **Limiar sempre como múltiplo do piso, nunca absoluto.**

**Teto de rodadas desproporcional.** Com 50 candidatos e piso ~7, o instrumento não distingue melhor que ~7 filmes. Gastar 14 rodadas nisso é desperdício — teto 8 basta.

**Rerank semântico pode não ajudar em catálogo pequeno.** Num contexto de 50 filmes, o rerank deu 48% de mesmo-cluster contra 48,7% do aleatório pareado dentro da mesma janela: nada. Testar por contexto, não assumir.

### Os dois baselines que decidem

- **Aleatório do catálogo inteiro.** Se o posterior não bate 3 filmes sorteados do catálogo, o quiz não está fazendo nada. (No contexto de 50: posterior 44% contra 30,5% aleatório, e alvo no top-3 12% contra 6,1% — o quiz funciona.)
- **Aleatório dentro da janela do rerank.** Decide se a camada semântica entra ou não naquele contexto.

Conclusão de produto que vale generalizar: **quiz vale a pena em catálogo pequeno, rerank semântico não necessariamente.** Publica sem rerank quando ele não bater o aleatório pareado.
