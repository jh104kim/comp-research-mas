# 2026년 기준 압축기 경쟁사 특별 리포트

생성일: 2026-06-25T20:43:10
분석 범위: 2025년 하반기(7~12월) vs 2026년 상반기(1~6월)
총 evidence: 136건

## 1. 구간별 수집 건수
- 2025 H2: 70건
- 2026 H1: 66건

## 2. 압축기별 삼성 인사이트
- Re(왕복동(Reciprocating)): 62건. 주요 경쟁사 Embraco/Nidec, GMCC/Midea, LG, Secop, 업계/R290. 주요 냉매 R290, R600a, R32, R454B.
- Ro(로터리(Rotary)): 27건. 주요 경쟁사 LG, GMCC/Midea, 규격/ASHRAE, JARN. 주요 냉매 R32, R290.
- Sc(스크롤(Scroll)): 47건. 주요 경쟁사 Copeland/Emerson, Danfoss, 규제/EU, AHR Expo. 주요 냉매 R454B, R410A.

## 3. 주요 출처
- GMCC compressor official monitoring 2025-07 (12건): https://www.gmcc.com
- LG Compressor official monitoring 2025-07 (12건): https://www.lg.com/global/business/compressor
- LG Rotary Compressor official monitoring 2025-07 (12건): https://www.lg.com/global/business/compressor-motor/compressors/rotary-compressor/
- Copeland official R454B scroll monitoring 2025-07 (12건): https://www.copeland.com/
- Danfoss compressors official monitoring 2025-07 (12건): https://www.danfoss.com/en/products/dcs/compressors/
- Embraco official R290 monitoring 2025-07 (12건): https://www.embraco.com/
- Secop official sustainable compressor monitoring 2025-07 (12건): https://www.secop.com/
- Copeland scroll heat pump applications reference 2025-07 (12건): https://www.coolingpost.com/products/copeland-scrolls-for-heat-pump-applications/
- EPA SNAP monitoring 2025-07 (10건): https://www.epa.gov/snap
- EU F-Gas monitoring 2025-07 (9건): https://climate.ec.europa.eu/eu-action/fluorinated-greenhouse-gases
- Google Patents GMCC Midea rotary compressor R290 2025 (6건): https://patents.google.com/?q=(GMCC+Midea+rotary+compressor+R290+2025)
- Google Patents GMCC Midea rotary compressor R290 2026 (6건): https://patents.google.com/?q=(GMCC+Midea+rotary+compressor+R290+2026)
- Google Patents search: compressor R290 2025 (1건): https://patents.google.com/?q=(compressor+R290+2025)
- 2025 LG CM Catalog Rotary compressor preview (1건): https://www.lg.com/global/images/business/compressor-motor/resource-download/pdf-file/2025_LG_CM_Catalog_Rotary%20compressor_preview.pdf
- Google Patents search: Copeland scroll compressor R454B patent (1건): https://patents.google.com/?q=(Copeland+scroll+compressor+R454B+patent)
- AHR Expo source monitoring 2026-01 (1건): https://www.ahrexpo.com/
- ASHRAE standards monitoring 2026-01 (1건): https://www.ashrae.org/technical-resources/standards-and-guidelines
- China Refrigeration Expo monitoring 2026-04 (1건): https://www.cr-expo.com/
- R290 Accounted for 38% of New EU Residential Heat Pump Certifications in 2024, According to Heat Pumps Watch (1건): https://naturalrefrigerants.com/news/heat-pump-watch-r290-eu-residential-heat-pumps-certificates/
- Embraco Launches R290 Condensing Units for European Market, Targeting Foodservice (1건): https://hydrocarbons21.com/embraco-debuts-r290-condensing-units-for-european-market-targeting-foodservice/

## 4. 실행 방법

```bash
uv sync --extra test
uv run python -m comp_research_mas.cli build-special-report --send-email
```
