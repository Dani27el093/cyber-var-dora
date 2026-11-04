# Business case: VaR cibernético y DORA

## Resumen ejecutivo

- El modelo estima una **pérdida anual por ciberriesgo** mediante Poisson compuesto: frecuencia de incidentes materiales × severidad de cada incidente.
- Para un banco europeo de referencia (15.000 M€ de ingresos, 6.000 M€ de CET1), el **VaR al 99,9%** con λ=5 oscila entre **705 M€ y 10.796 M€** según el modelo de severidad. La estimación central (Weibull de finanzas) es **1.753 M€**; el escenario de estrés (Lognormal pooled) es **10.796 M€**.
- La pérdida esperada en la cola (ES 99,9%) va de **2.573 M€ a 30.921 M€**. Un evento de esa magnitud pondría en riesgo la solvencia y la continuidad del negocio.
- **Conclusión:** el VaR no debe usarse como una cifra única de capital. Debe integrarse en el apetito de riesgo, el stress testing y la priorización de inversiones en resiliencia (DORA), y recalibrarse con datos internos.

> **Aclaración regulatoria.** DORA (Reglamento (UE) 2022/2554) exige un marco de gestión del riesgo TIC, identificación de riesgos, pruebas de resiliencia y gestión de terceros, pero **no prescribe una fórmula de VaR ni un capital regulatorio único**. Los requerimientos de fondos propios por riesgo operacional se rigen por CRR/CRD. Aquí el VaR es **capital económico interno** y herramienta de apetito de riesgo, no una cifra regulatoria.

## 1. Entidad de referencia

Para traducir el VaR a magnitudes de negocio se usa una entidad ilustrativa:

| Parámetro | Valor |
|---|---:|
| Ingresos anuales | 15.000 M€ |
| Capital CET1 | 6.000 M€ |
| Empleados | 80.000 |
| Incidentes materiales al año (λ base) | 5 |

No es una entidad real; permite comparar el VaR con métricas de solvencia y rentabilidad.

## 2. Resultados por escenario

| Escenario | Modelo | λ | VaR 99,9% (M€) | % ingresos | % CET1 | ES 99,9% (M€) |
|---|---|---:|---:|---:|---:|---:|
| Inferior | Gamma finanzas | 5 | 705 | 4,7% | 11,8% | 809 |
| **Central** | **Weibull finanzas** | **5** | **1.753** | **11,7%** | **29,2%** | **2.573** |
| Conservador | Lognormal finanzas | 5 | 6.939 | 46,3% | 115,7% | 16.448 |
| Estrés | Lognormal pooled | 5 | 10.796 | 72,0% | 179,9% | 30.921 |

**Lectura:** incluso el escenario central consume ~29% del CET1 en un año 1-de-1.000. El escenario de estrés supera el capital disponible: sería un evento de supervivencia, no solo de pérdidas.

### Sensibilidad a la frecuencia

Con el modelo Lognormal pooled:

| λ | VaR 99,9% (M€) | ES 99,9% (M€) |
|---:|---:|---:|
| 1 | 3.353 | 11.827 |
| 5 | 10.796 | 30.921 |
| 20 | 31.542 | 107.651 |

El VaR crece con λ, pero de forma **sublineal**: pasar de 5 a 20 multiplica λ por 4 y el VaR por ~2,9. La razón es que, al agregar más eventos, la masa de la distribución se desplaza, pero el percentil extremo no escala linealmente con la frecuencia.

## 3. Por qué esto importa para DORA

DORA no exige calcular un VaR, pero el modelo aporta evidencia cuantitativa para varios requisitos:

| Requisito DORA | Uso del modelo |
|---|---|
| **Art. 6** — Marco de gestión del riesgo TIC | Cuantifica el riesgo residual y informa el apetito de riesgo aprobado por el órgano de dirección. |
| **Art. 8** — Identificación de riesgos TIC | Traduce el catálogo de incidentes en una distribución de pérdidas y prioriza los riesgos materiales. |
| **Art. 9** — Protección y prevención | Permite evaluar el retorno de los controles: reducir λ o la severidad de la cola reduce el VaR y el ES. |
| **Art. 11** — Continuidad y recuperación | El ES 99,9% orienta los objetivos de recuperación y la tolerancia al impacto. |
| **Arts. 24-27** — Pruebas de resiliencia | Los escenarios de λ y severidad alimentan el diseño de pruebas y el *threat-led penetration testing*. |
| **Arts. 28-30** — Riesgo de terceros | Permite cuantificar la concentración de proveedores TIC y fijar límites contractuales. |
| **Arts. 17-19** — Gestión y notificación de incidentes | Los datos de pérdidas internas permiten recalibrar el modelo y cerrar el ciclo de mejora. |

## 4. Decisiones de negocio recomendadas

1. **Apetito de riesgo:** fijar un límite de VaR 99,9% (por ejemplo, ≤15% del CET1) y reportarlo trimestralmente al comité de riesgos. Con el escenario central (29% del CET1), el banco estaría por encima de ese límite y debería actuar.
2. **Priorizar resiliencia sobre capital:** reducir λ mediante detección, respuesta y continuidad es más eficiente que acumular capital para un evento de 10.000 M€. El ES de 30.921 M€ en el escenario de estrés no es financiable con capital.
3. **Stress testing:** usar λ=20 y Lognormal como escenario adverso; complementar con escenarios de ciberataque sistémico, fallo de un proveedor cloud y ransomware con interrupción prolongada.
4. **Transferencia de riesgo:** evaluar ciberseguros para la cola; el ES 99,9% justifica una cobertura alta, aunque el mercado puede no tener capacidad para un evento de 30.000 M€.
5. **Datos internos:** el VCDB es público y está sesgado a incidentes mediáticos. El banco debe construir un registro interno de pérdidas (importe, fecha, tipo de evento, causa, recuperación) y recalibrar anualmente.
6. **Gobernanza:** presentar el VaR como **rango** (no como cifra única), junto con el modelo, los supuestos y la incertidumbre. La diapositiva de una sola cifra es engañosa.

## 5. Limitaciones que el comité debe conocer

- La frecuencia λ es un **supuesto**, no una estimación del VCDB.
- La muestra de finanzas es pequeña (49 pérdidas por encima del umbral); la muestra *pooled* mejora la estimación pero asume homogeneidad entre sectores.
- El VaR al 99,9% cambia más de un orden de magnitud entre modelos; el resultado es un **rango de model risk**, no una medida precisa.
- No se modelan dependencias, ciberataques sistémicos ni pérdidas reputacionales no monetizadas.
- La normalización monetaria usa tipos medios anuales e inflación de la eurozona; no sustituye a un registro interno de pérdidas.

## 6. Conclusión

El proyecto demuestra que el ciberriesgo es **cuantificable, pero no con una precisión falsa**. La combinación de Poisson compuesto, ajuste truncado de colas y Montecarlo produce una distribución de pérdidas útil para:

- fijar apetito de riesgo y límites;
- priorizar inversiones en controles;
- diseñar stress tests y pruebas de resiliencia;
- justificar ante el regulador y el consejo que la entidad mide y gestiona su riesgo TIC.

La conclusión para DORA no es "reservar X millones", sino **demostrar que la entidad entiende su exposición, la mide con datos, conoce la incertidumbre y actúa en consecuencia**.
