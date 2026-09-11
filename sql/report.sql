WITH current_period AS (
    SELECT
        vp2."Naimenovanie" AS "Основной менеджер",
        (vp."Kod" || mkm."VidNomenklatury") AS "Ключ",
        vp."Kod" AS "Код",
        vp."Naimenovanie" AS "Партнер",
        mkm."VidNomenklatury" AS "Номенклатура.Вид номенклатуры",
        SUM(r."Summa") AS "Выручка текущий период"
    FROM "RTS" r
    LEFT JOIN "v1_Partnery" vp ON r."PartnerGuid" = vp."SsylkaGuid"
    LEFT JOIN "v1_Polzovateli" vp2 ON vp2."SsylkaGuid" = vp."OsnovnoyMenedzherGuid"
    LEFT JOIN "MatritsaKatMen" mkm ON r."NomenklaturaGuid" = mkm."SsylkaGuid"
    WHERE
        vp."OsnovnoyMenedzherOtdely_Polzovateli_" = 'Отдел Дистрибуции'
        AND r."Data" >= :cur_start AND r."Data" < :cur_end
        AND mkm."Group_1" NOT IN ('01Бухгалтерские', '02Прочее (счет 41)', 'Аренда номенклатуры', 'Некондиция', 'Услуги, распродажа, тара, номенклатура сайт, комплектующие')
    GROUP BY vp2."Naimenovanie", vp."Kod", vp."Naimenovanie", mkm."VidNomenklatury"
),
previous_period AS (
    SELECT
        vp2."Naimenovanie" AS "Основной менеджер",
        (vp."Kod" || mkm."VidNomenklatury") AS "Ключ",
        vp."Kod" AS "Код",
        vp."Naimenovanie" AS "Партнер",
        mkm."VidNomenklatury" AS "Номенклатура.Вид номенклатуры",
        SUM(r."Summa") AS "Выручка период сравнения"
    FROM "RTS" r
    LEFT JOIN "v1_Partnery" vp ON r."PartnerGuid" = vp."SsylkaGuid"
    LEFT JOIN "v1_Polzovateli" vp2 ON vp2."SsylkaGuid" = vp."OsnovnoyMenedzherGuid"
    LEFT JOIN "MatritsaKatMen" mkm ON r."NomenklaturaGuid" = mkm."SsylkaGuid"
    WHERE
        vp."OsnovnoyMenedzherOtdely_Polzovateli_" = 'Отдел Дистрибуции'
        AND r."Data" >= :prev_start AND r."Data" < :prev_end
        AND mkm."Group_1" NOT IN ('01Бухгалтерские', '02Прочее (счет 41)', 'Аренда номенклатуры', 'Некондиция', 'Услуги, распродажа, тара, номенклатура сайт, комплектующие')
    GROUP BY vp2."Naimenovanie", vp."Kod", vp."Naimenovanie", mkm."VidNomenklatury"
),
future_period AS (
    SELECT
        vp2."Naimenovanie" AS "Основной менеджер",
        (vp."Kod" || mkm."VidNomenklatury") AS "Ключ",
        vp."Kod" AS "Код",
        vp."Naimenovanie" AS "Партнер",
        mkm."VidNomenklatury" AS "Номенклатура.Вид номенклатуры",
        SUM(r."Summa") AS "Выручка третий период"
    FROM "RTS" r
    LEFT JOIN "v1_Partnery" vp ON r."PartnerGuid" = vp."SsylkaGuid"
    LEFT JOIN "v1_Polzovateli" vp2 ON vp2."SsylkaGuid" = vp."OsnovnoyMenedzherGuid"
    LEFT JOIN "MatritsaKatMen" mkm ON r."NomenklaturaGuid" = mkm."SsylkaGuid"
    WHERE
        vp."OsnovnoyMenedzherOtdely_Polzovateli_" = 'Отдел Дистрибуции'
        AND r."Data" >= :fut_start AND r."Data" < :fut_end
        AND mkm."Group_1" NOT IN ('01Бухгалтерские', '02Прочее (счет 41)', 'Аренда номенклатуры', 'Некондиция', 'Услуги, распродажа, тара, номенклатура сайт, комплектующие')
    GROUP BY vp2."Naimenovanie", vp."Kod", vp."Naimenovanie", mkm."VidNomenklatury"
)
SELECT
    COALESCE(c."Основной менеджер", p."Основной менеджер", f."Основной менеджер") AS "Основной менеджер",
    COALESCE(c."Ключ", p."Ключ", f."Ключ") AS "Ключ",
    COALESCE(c."Код", p."Код", f."Код") AS "Код",
    COALESCE(c."Партнер", p."Партнер", f."Партнер") AS "Партнер",
    COALESCE(c."Номенклатура.Вид номенклатуры", p."Номенклатура.Вид номенклатуры", f."Номенклатура.Вид номенклатуры") AS "Номенклатура.Вид номенклатуры",
    COALESCE(p."Выручка период сравнения", 0) AS "Выручка период сравнения",
    COALESCE(c."Выручка текущий период", 0) AS "Выручка текущий период",
    COALESCE(f."Выручка третий период", 0) AS "Выручка третий период",
    COALESCE(c."Выручка текущий период", 0) - COALESCE(p."Выручка период сравнения", 0) AS "Абсолютный прирост",
    CASE
        WHEN COALESCE(p."Выручка период сравнения", 0) = 0 THEN NULL
        ELSE ROUND((COALESCE(c."Выручка текущий период", 0) / COALESCE(p."Выручка период сравнения", 0) - 1) * 100, 2)
    END AS "Относительный прирост",
    CASE
        WHEN COALESCE(p."Выручка период сравнения", 0) > 0
            AND COALESCE(c."Выручка текущий период", 0) < COALESCE(p."Выручка период сравнения", 0)
            AND (COALESCE(p."Выручка период сравнения", 0) - COALESCE(c."Выручка текущий период", 0)) > 20000
            AND ((COALESCE(p."Выручка период сравнения", 0) - COALESCE(c."Выручка текущий период", 0)) / COALESCE(p."Выручка период сравнения", 0) * 100) > 50
        THEN 'Да' ELSE 'Нет'
    END AS "Падение"
FROM current_period c
FULL OUTER JOIN previous_period p
    ON c."Основной менеджер" = p."Основной менеджер"
    AND c."Ключ" = p."Ключ"
    AND c."Партнер" = p."Партнер"
    AND c."Номенклатура.Вид номенклатуры" = p."Номенклатура.Вид номенклатуры"
FULL OUTER JOIN future_period f
    ON COALESCE(c."Основной менеджер", p."Основной менеджер") = f."Основной менеджер"
    AND COALESCE(c."Ключ", p."Ключ") = f."Ключ"
    AND COALESCE(c."Партнер", p."Партнер") = f."Партнер"
    AND COALESCE(c."Номенклатура.Вид номенклатуры", p."Номенклатура.Вид номенклатуры") = f."Номенклатура.Вид номенклатуры"
ORDER BY
    COALESCE(c."Основной менеджер", p."Основной менеджер", f."Основной менеджер"),
    COALESCE(c."Партнер", p."Партнер", f."Партнер"),
    COALESCE(c."Ключ", p."Ключ", f."Ключ"),
    COALESCE(c."Номенклатура.Вид номенклатуры", p."Номенклатура.Вид номенклатуры", f."Номенклатура.Вид номенклатуры")