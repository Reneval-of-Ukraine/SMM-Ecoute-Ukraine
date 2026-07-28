# Écoute Ukraine — автопостинг (Telegram + Facebook + Instagram)

Готовые файлы для GitHub-репозитория, который публикует посты из `posts_queue.json`
по расписанию через GitHub Actions. LinkedIn и WhatsApp сюда не входят — там
отдельная механика (WhatsApp вообще не лента, а рассылки), настроим отдельно.

## Что в комплекте

```
poster_action.py                 — публикующий скрипт (TG/FB/IG)
get_long_token.py                — разовый помощник для обмена Facebook-токена
build_queue.py                   — генератор очереди из Month_1 (уже отработал один раз)
posts_queue.json                 — очередь постов (23 поста на месяц, из Month_1 пака)
.github/workflows/post-scheduler.yml  — GitHub Actions workflow (cron раз в 10 мин)
IMAGES_NEEDED.txt                — список всех 55 файлов картинок, которые должны лежать в images/
```

## Шаг 1 — репозиторий (готово)

Репозиторий создан и заполнен: `github.com/Reneval-of-Ukraine/SMM-Ecoute-Ukraine`
(публичный — это нужно, чтобы Facebook/Instagram API могли скачивать картинки
по прямой ссылке `raw.githubusercontent.com`). Все файлы кода и все 55 картинок
в `images/<Content ID>/...` уже загружены.

Если понадобится загружать картинки заново (например, для новых постов) —
загружайте по одной подпапке за раз через **Add file → Upload files**: GitHub
web-загрузчик отказывает с ошибкой "The file is too large" при попытке
закинуть больше ~100 МБ суммарно за один коммит, а одна подпапка Content ID
(1-6 картинок, обычно 1-15 МБ) всегда укладывается с запасом.

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

## Список изображений (все 23 поста, 55 файлов) — уже загружены

Полный актуальный список также лежит в `IMAGES_NEEDED.txt` рядом с этим README.

```
images/TG-17/EU_UA_TG_TG-17_Monthly_recap_1080x1350.png
images/UA-01/EU_UA_IG_UA-01_S01_Cover_Koly_tryvoha_nakryvaie_1080x1350.png
images/UA-01/EU_UA_IG_UA-01_S02_Povilno_vydykhnit_1080x1350.png
images/UA-01/EU_UA_IG_UA-01_S03_Nazvit_5_predmetiv_1080x1350.png
images/UA-01/EU_UA_IG_UA-01_S04_Vidchuyte_oporu_pid_nohamy_1080x1350.png
images/UA-01/EU_UA_IG_UA-01_S05_Ruka_na_hrudy_abo_zhyvit_1080x1350.png
images/UA-01/EU_UA_IG_UA-01_S06_Tse_myne_Zberezhit_sobi_1080x1350.png
images/UA-02/EU_UA_TG_UA-02_Malenka_praktyka_zazemlennya_1080x1350.png
images/FR-01-FB/EU_FR_FB_FR-01-FB_Sante_mentale_reste_une_priorite_1200x1500.png
images/UA-04/EU_UA_TG_UA-04_Tilo_tezh_vtomliuietsia_vid_stresu_1080x1350.png
images/UA-03/EU_UA_IG_UA-03_S01_Cover_Mif_ya_mayu_vporatysia_sam_sama_1080x1350.png
images/UA-03/EU_UA_IG_UA-03_S02_Potreba_v_pidtrymtsi_ne_slabkist_1080x1350.png
images/UA-03/EU_UA_IG_UA-03_S03_Ne_zobovyazani_naodyntsi_1080x1350.png
images/UA-03/EU_UA_IG_UA-03_S04_Pidtrymka_pochynaietsia_z_maloho_1080x1350.png
images/UA-03/EU_UA_IG_UA-03_S05_Prosyty_pro_dopomohu_normalno_1080x1350.png
images/UA-08/EU_UA_TG_UA-08_Miaka_praktyka_dykhannia_1080x1350.png
images/FR-03/EU_FR_FB_FR-03_Lexil_ne_se_voit_pas_toujours_1200x630.png
images/UA-05/EU_UA_IG_UA-05_S01_Cover_Yak_pidtrymaty_dytynu_1080x1350.png
images/UA-05/EU_UA_IG_UA-05_S02_Dity_ne_zavzhdy_hovoriat_1080x1350.png
images/UA-05/EU_UA_IG_UA-05_S03_Perdbachuvanist_dopomahaie_1080x1350.png
images/UA-05/EU_UA_IG_UA-05_S04_Menshe_tysku_bilshe_prysutnosti_1080x1350.png
images/UA-05/EU_UA_IG_UA-05_S05_Dozvolte_emotsiiam_buty_bez_osudu_1080x1350.png
images/UA-05/EU_UA_IG_UA-05_S06_Doroslyi_yakyi_poruch_1080x1350.png
images/UA-10/EU_UA_TG_UA-10_Shcho_zrobyty_koly_vazhko_zasnuty_1080x1350.png
images/FR-05/EU_FR_FB_FR-05_Soutien_durable_partenariats_1200x1500.png
images/UA-12/EU_UA_TG_UA-12_Koly_khochetsia_movchaty_1080x1350.png
images/UA-07/EU_UA_IG_UA-07_S01_Cover_Adaptatsiia_u_Frantsii_1080x1350.png
images/UA-07/EU_UA_IG_UA-07_S02_Bezpeka_ne_zavzhdy_prynosyt_polehshennia_1080x1350.png
images/UA-07/EU_UA_IG_UA-07_S03_Nova_mova_novi_pravyla_novyi_temp_1080x1350.png
images/UA-07/EU_UA_IG_UA-07_S04_Samotnist_i_provyna_1080x1350.png
images/UA-07/EU_UA_IG_UA-07_S05_Adaptatsiia_tse_protses_1080x1350.png
images/UA-07/EU_UA_IG_UA-07_S06_Budte_do_sebe_miakshymy_1080x1350.png
images/UA-14/EU_UA_TG_UA-14_Malenka_opora_na_sohodni_1080x1350.png
images/FR-07/EU_FR_FB_FR-07_Lexil_traces_invisibles_1200x1500.png
images/UA-09/EU_UA_IG_UA-09_S01_Cover_5_fraz_yaki_pidtrymuiut_1080x1350.png
images/UA-09/EU_UA_IG_UA-09_S02_Ya_poruch_1080x1350.png
images/UA-09/EU_UA_IG_UA-09_S03_Te_shcho_ty_vidchuvaiesh_maie_sens_1080x1350.png
images/UA-09/EU_UA_IG_UA-09_S04_Ty_ne_musysh_prokhodyty_tse_naodyntsi_1080x1350.png
images/UA-09/EU_UA_IG_UA-09_S05_Chym_ya_mozhu_tebe_pidtrymaty_1080x1350.png
images/UA-09/EU_UA_IG_UA-09_S06_Tobi_ne_treba_buty_sylnym_shchomyti_1080x1350.png
images/FB-BI-01/EU_MIXED_FB_FB-BI-01_Pidtrymka_Solidarite_1200x1500.png
images/UA-13/EU_UA_IG_UA-13_S01_Cover_Yak_zrozumity_potribna_pidtrymka_1080x1350.png
images/UA-13/EU_UA_IG_UA-13_S02_Vazhche_spravliatysia_1080x1350.png
images/UA-13/EU_UA_IG_UA-13_S03_Tryvoha_napruha_vtoma_1080x1350.png
images/UA-13/EU_UA_IG_UA-13_S04_Khochetsia_viddalytysia_i_movchaty_1080x1350.png
images/UA-13/EU_UA_IG_UA-13_S05_Dumka_pro_pidtrymku_prynosyt_polehshennia_1080x1350.png
images/FB-UA-01/EU_UA_FB_FB-UA-01_Ecoute_Ukraine_poruch_1200x630_correct_logo.png
images/UA-15/EU_UA_IG_UA-15_S01_5_povilnykh_vdykhiv_i_vydykhiv_1080x1350.png
images/UA-15/EU_UA_IG_UA-15_S02_Vypiyte_sklianku_vody_1080x1350.png
images/UA-15/EU_UA_IG_UA-15_S03_Vidiydit_vid_ekrana_1080x1350.png
images/UA-15/EU_UA_IG_UA-15_S04_Skazhit_sobi_odnu_dobru_frazu_1080x1350.png
images/UA-15/EU_UA_IG_UA-15_S05_Malenkyi_vidpochynok_1080x1350.png
images/FB-UA-02/EU_UA_FB_FB-UA-02_Pidtrymka_ditei_pochynaietsia_z_prostykh_rechei_1200x1500.png
images/FB-UA-03/EU_UA_FB_FB-UA-03_Pidtrymka_poruch_daleko_vid_domu_1200x1500.png
images/FB-UA-04/EU_UA_FB_FB-UA-04_Ne_vse_treba_vytrymuvaty_naodyntsi_1200x1500.png
```

Дальше очередь можно расширять теми же полями — Stories (STORY-*) и видео
(VIDEO-*) из `Month_1/` сюда сознательно не включены, для них нужна отдельная
логика в `poster_action.py` (другой API-эндпоинт). Новый контент на следующий
месяц можно добавлять вручную по образцу существующих записей, либо перезапустить
`build_queue.py` на обновлённой папке `Month_1/`.
