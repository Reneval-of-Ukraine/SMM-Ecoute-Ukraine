# Écoute Ukraine — автопостинг (Telegram + Facebook + Instagram)

Готовые файлы для GitHub-репозитория, который публикует посты из `posts_queue.json`
по расписанию через GitHub Actions. LinkedIn и WhatsApp сюда не входят — там
отдельная механика (WhatsApp вообще не лента, а рассылки), настроим отдельно.

## Что в комплекте

```
poster_action.py                 — публикующий скрипт (TG/FB/IG)
get_long_token.py                — разовый помощник для обмена Facebook-токена
posts_queue.json                 — очередь постов (8 стартовых, из Month_1 пака)
.github/workflows/post-scheduler.yml  — GitHub Actions workflow (cron раз в 10 мин)
```

## Шаг 1 — создать репозиторий

1. Создайте новый **приватный** репозиторий на GitHub, например `ecoute-ukraine-autoposting`.
2. Загрузите в него все файлы из этого комплекта, сохранив структуру папок.
3. Создайте папку `images/` и положите туда картинки — по одной подпапке на
   Content ID (`images/UA-01/...png`, `images/FB-UA-01/...png` и т.д.), как в
   исходной папке `Month_1`. Список нужных файлов для стартовых 8 постов — ниже.
4. **Картинки должны быть доступны публично** через
   `raw.githubusercontent.com` — если репозиторий приватный, поставьте раздачу
   через отдельный **публичный** репозиторий/ветку только для картинок, либо
   сделайте публичной эту конкретную ветку/папку. Простейший вариант — держать
   картинки в отдельном публичном репозитории `ecoute-ukraine-images`, а код
   (`poster_action.py`, токены, очередь) — в приватном.
5. В `posts_queue.json` замените `Reneval-of-Ukraine/SMM-Ecoute-Ukraine` в каждом `image_url`/`ig_image_urls`
   на реальные `<ваш GitHub логин>/<название репозитория с картинками>`.

## Шаг 2 — секреты в GitHub

Settings → Secrets and variables → Actions → New repository secret:

| Secret | Значение |
|---|---|
| `GH_PAT` | Fine-grained Personal Access Token только для этого репозитория, право Contents: Read and write |
| `BOT_TOKEN` | Токен вашего Telegram-бота (уже есть: `8968010230:...`) |
| `CHANNEL_ID` | ID вашего Telegram-канала (узнать через @username_to_id_bot) |
| `FB_PAGE_ACCESS_TOKEN` | Долгосрочный Page Token (см. Шаг 3) |
| `FB_PAGE_ID` | ID бизнес-страницы Facebook |
| `IG_USER_TOKEN` | Долгосрочный user-токен (~60 дней, см. Шаг 3) |
| `IG_ACCOUNT_ID` | Instagram Business Account ID |

`GH_PAT` создаётся в GitHub: Settings → Developer settings → Personal access
tokens → Fine-grained tokens → выбрать конкретно этот репозиторий → Contents:
Read and write.

## Шаг 3 — Meta (Facebook + Instagram)

Идём строго по вашему проверенному playbook (`AUTOPOSTING_MASTER_PLAYBOOK.md`),
самые частые ловушки:

1. При создании приложения на developers.facebook.com сразу выбрать **оба**
   use case вместе: **Instagram API** + **Pages API** (Manage Pages). Если
   выбрать только Facebook Login — приложение станет Consumer-типа и Instagram
   потом не добавится никогда, придётся создавать новое.
2. Для публикации — раздел **«Настройка API для входа на Facebook»**, не
   messaging-раздел.
3. Разрешение `pages_manage_posts` ищите внутри use case **Manage Pages** →
   вкладка «Разрешения и функции».
4. Приложение должно быть переведено в **Live**-режим ДО генерации финальных
   токенов (Настройки → Основные → указать Privacy Policy URL → Опубликовать).
5. Получить токены (используйте `get_long_token.py`):
   - Graph API Explorer → выдать права `pages_show_list`,
     `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`,
     `instagram_content_publishing`, `business_management` → сгенерировать
     **User Token**.
   - Обменять на долгосрочный:
     `python get_long_token.py APP_ID APP_SECRET SHORT_LIVED_USER_TOKEN`
   - Скрипт покажет `IG_USER_TOKEN`, список ваших Page ID + их
     `FB_PAGE_ACCESS_TOKEN` (берите **отсюда**, не из кнопки в Explorer —
     иначе токен проживёт полтора часа и незаметно перестанет работать).
   - `IG_ACCOUNT_ID` получить отдельным запросом:
     `curl "https://graph.facebook.com/v21.0/<FB_PAGE_ID>?fields=instagram_business_account&access_token=<FB_PAGE_ACCESS_TOKEN>"`

## Шаг 4 — тест перед боевым запуском

1. Запустить workflow вручную (Actions → Post Scheduler → Run workflow) с
   `dry_run: 1` — убедиться, что скрипт видит due-посты и не падает.
2. Поставить одному тестовому посту `scheduled_time` на "прямо сейчас", убрать
   dry_run, запустить вручную ещё раз.
3. Проверить результат вручную в самом канале/странице/аккаунте — зелёная
   галочка в Actions означает только то, что скрипт не упал, а не что
   конкретная платформа реально опубликовала (ошибки по отдельным площадкам
   логируются, но не останавливают весь job).

## Как выглядит расписание дальше

Раз пост помечен `published: true`, автоматически он больше никогда не
повторится — даже если упала только одна из платформ. Чтобы повторить только
упавшую площадку: верните `published: false` и сузьте `platforms` до
провалившихся, затем запустите workflow вручную (не ждите ближайший cron —
возможна гонка с автокоммитом).

## Список изображений для стартовых 8 постов

```
images/UA-01/EU_UA_IG_UA-01_S01_Cover_Koly_tryvoha_nakryvaie_1080x1350.png
images/UA-01/EU_UA_IG_UA-01_S02_Povilno_vydykhnit_1080x1350.png
images/UA-01/EU_UA_IG_UA-01_S03_Nazvit_5_predmetiv_1080x1350.png
images/UA-01/EU_UA_IG_UA-01_S04_Vidchuyte_oporu_pid_nohamy_1080x1350.png
images/UA-01/EU_UA_IG_UA-01_S05_Ruka_na_hrudy_abo_zhyvit_1080x1350.png
images/UA-01/EU_UA_IG_UA-01_S06_Tse_myne_Zberezhit_sobi_1080x1350.png
images/UA-02/EU_UA_TG_UA-02_Malenka_praktyka_zazemlennya_1080x1350.png
images/UA-03/EU_UA_IG_UA-03_S01_Cover_Mif_ya_mayu_vporatysia_sam_sama_1080x1350.png
images/UA-03/EU_UA_IG_UA-03_S02_Potreba_v_pidtrymtsi_ne_slabkist_1080x1350.png
images/UA-03/EU_UA_IG_UA-03_S03_Ne_zobovyazani_naodyntsi_1080x1350.png
images/UA-03/EU_UA_IG_UA-03_S04_Pidtrymka_pochynaietsia_z_maloho_1080x1350.png
images/UA-03/EU_UA_IG_UA-03_S05_Prosyty_pro_dopomohu_normalno_1080x1350.png
images/FB-UA-01/EU_UA_FB_FB-UA-01_Ecoute_Ukraine_poruch_1200x630_correct_logo.png
images/UA-04/EU_UA_TG_UA-04_Tilo_tezh_vtomliuietsia_vid_stresu_1080x1350.png
images/FR-01-FB/EU_FR_FB_FR-01-FB_Sante_mentale_reste_une_priorite_1200x1500.png
images/UA-05/EU_UA_IG_UA-05_S01_Cover_Yak_pidtrymaty_dytynu_1080x1350.png
images/UA-05/EU_UA_IG_UA-05_S02_Dity_ne_zavzhdy_hovoriat_1080x1350.png
images/UA-05/EU_UA_IG_UA-05_S03_Perdbachuvanist_dopomahaie_1080x1350.png
images/UA-05/EU_UA_IG_UA-05_S04_Menshe_tysku_bilshe_prysutnosti_1080x1350.png
images/UA-05/EU_UA_IG_UA-05_S05_Dozvolte_emotsiiam_buty_bez_osudu_1080x1350.png
images/UA-05/EU_UA_IG_UA-05_S06_Doroslyi_yakyi_poruch_1080x1350.png
images/FB-UA-02/EU_UA_FB_FB-UA-02_Pidtrymka_ditei_pochynaietsia_z_prostykh_rechei_1200x1500.png
```

Дальше очередь можно расширять теми же полями — весь остальной контент уже
готов в `Month_1/`, просто добавляйте новые записи в `posts_queue.json` по
образцу существующих.
