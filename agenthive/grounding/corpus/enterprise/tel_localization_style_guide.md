# Kestrava Localization Style Guide

How Kestrava Telecom copy is localised from English into its five consumer markets. The Localization agent's reviewer checks every rule below.

Fictional style guide for the Wursta Agent Hive demo. Kestrava Telecom is an invented company.

## Golden rules

1. **Never convert prices.** Each market has its own price sheet. Use the local price, never a currency conversion of the English price.
2. **Keep product names verbatim.** Do-not-translate: Kestrava, Kestrava Fiber Max, Kestrava 5G Home, Kestrava One, Kestrava Wi-Fi 7 Gateway, Wi-Fi 7, 5G, Gig.
3. **Translate meaning and tone, not words.** Keep the call to action as an imperative.
4. **Dates:** DD/MM or the month name. US-style dates such as 12/31 are not allowed.
5. **Legal lines** must use the local wording below, not a translation of the English line.

## Locale profiles

| Locale | Form of address | Price format | Tax line | Terms line | Fair-use line | SMS opt-out | Expansion |
|---|---|---|---|---|---|---|---|
| es-419 | tú (never usted) | US$65 al mes | Impuestos y cargos no incluidos. | Aplican términos y condiciones. | Aplica política de uso razonable. | Responde STOP para no recibir más mensajes | about 1.25x |
| es-ES | tú | 49,90 €/mes | IVA incluido. | Consulta condiciones. | Sujeto a política de uso razonable. | Responde BAJA para no recibir más mensajes | about 1.25x |
| pt-BR | você (no tu, o senhor, a senhora) | R$ 249,90/mês | Impostos inclusos. | Consulte condições. | Sujeito à política de uso justo. | Responda SAIR para não receber mais mensagens | about 1.2x |
| fr-CA | vous | 79 $/mois | Taxes en sus. | Certaines conditions s'appliquent. | Politique d'utilisation équitable applicable. | Répondez STOP pour vous désabonner | about 1.2x |
| fr-FR | vous | 44,99 €/mois | Prix TTC. | Voir conditions. | Soumis à une politique d'usage raisonnable. | STOP au 36180 | about 1.2x |

Prices in es-ES, pt-BR and fr-FR are always shown **tax-inclusive**; a line such as "no incluidos", "não inclusos" or "HT" is a blocker in those markets. es-ES, pt-BR, fr-CA and fr-FR use a decimal comma.

## Local price sheet (monthly, 12-month offer)

| Product | es-419 | es-ES | pt-BR | fr-CA | fr-FR |
|---|---|---|---|---|---|
| Kestrava Fiber Max 2 Gig | US$65/mes | 49,90 €/mes | R$ 249,90/mês | 79 $/mois | 44,99 €/mois |
| Kestrava 5G Home | US$50/mes | 39,90 €/mes | R$ 189,90/mês | 65 $/mois | 34,99 €/mois |

## Glossary

| English | es-419 | es-ES | pt-BR | fr-CA | fr-FR |
|---|---|---|---|---|---|
| plan | plan | tarifa | plano | forfait | forfait |
| data | datos | datos | dados | données | données |
| unlimited | ilimitado | ilimitado | ilimitado | illimité | illimité |
| router | módem | router | roteador | routeur | box |
| installation | instalación | instalación | instalação | installation | installation |
| speed | velocidad | velocidad | velocidade | vitesse | débit |
| fiber | fibra | fibra | fibra | fibre | fibre |
| coverage | cobertura | cobertura | cobertura | couverture | couverture |
| holiday season | fiestas de fin de año | Navidad | festas de fim de ano | temps des Fêtes | fêtes de fin d'année |
| sign up | contrata | contrata | assine | abonnez-vous | souscrivez |
| Black Friday | Black Friday | Black Friday | Black Friday | Vendredi fou | Black Friday |

## Anglicisms to avoid

- **fr-CA:** email and e-mail -> courriel; shopping -> magasinage; weekend -> fin de semaine; upgrade -> mise à niveau; deal -> aubaine; Black Friday -> Vendredi fou; streaming -> diffusion en continu.
- **fr-FR:** upgrade -> passez à; deal -> bon plan.
- **es-419:** upgrade -> mejora / pásate a; email -> correo; shopping -> compras.
- **es-ES:** upgrade -> mejora / pásate a; email -> correo electrónico.
- **pt-BR:** "upgrade" is acceptable.

## Cultural and seasonal notes

- **pt-BR:** December is summer in Brazil. No snow, winter, cold or cozy-fireplace imagery (inverno, neve, frio, the snowflake emoji). The OK-hand gesture emoji is offensive in Brazil. Thanksgiving is not celebrated.
- **es-419:** mixed hemispheres; keep December campaigns season-neutral (avoid nieve, invierno, snowflake).
- **fr-CA:** Canadian Thanksgiving (Action de grâce) is in October, not November.
- **es-ES and fr-FR:** northern hemisphere, winter imagery is fine; Thanksgiving is not celebrated.

## Channel limits after translation

Push 110, SMS 160 (including the local opt-out), social 280, email subject 50 characters. Tighten translations more than 0.15x above the expected expansion.

## Reviewer checklist

1. Do-not-translate terms verbatim; correct form of address.
2. Local price and format; local tax, terms and fair-use lines ("ilimitado" or "illimité" always needs the fair-use line).
3. No US-style dates, anglicisms or English fragments; decimal comma where required.
4. Cultural and seasonal flags cleared.
5. SMS ends with the local opt-out; length within the channel limit.
