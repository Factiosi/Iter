import { type ReactNode } from 'react';
import * as Accordion from '@radix-ui/react-accordion';
import { FeatherIcon } from '@/icons/feather';
import { AppPrimaryButton } from './AppPrimaryButton';

type InstructionItem = {
  id: string;
  title: string;
  content: ReactNode;
};

function Note({ children }: { children: ReactNode }) {
  return (
    <p className="mt-2 pl-3 border-l-2 border-[color-mix(in_srgb,var(--primary)_45%,transparent)] text-sm text-[var(--muted-foreground)]">
      {children}
    </p>
  );
}

function ImgPlaceholder() {
  return (
    <div
      className="my-3 py-5 px-4 rounded-lg border border-dashed border-[var(--border)] bg-[var(--background)]/50 text-center text-sm text-[var(--muted-foreground)]"
      aria-hidden
    >
      Изображение будет добавлено после настройки VPN
    </div>
  );
}

function HappDownloadButton({
  href,
  sourceCaption,
  children,
}: {
  href: string;
  /** Подпись источника (магазин / релиз) */
  sourceCaption: string;
  children: ReactNode;
}) {
  return (
    <div className="w-full rounded-lg border border-[var(--border)] bg-[var(--accordion-bg)]/60 p-4">
      <div className="space-y-3">
        <p className="text-xs text-[var(--muted-foreground)]">{sourceCaption}</p>
        <AppPrimaryButton asChild className="w-full">
          <a href={href} target="_blank" rel="noopener noreferrer">
            <FeatherIcon name="download" size={20} className="text-[var(--foreground)]" />
            {children}
          </a>
        </AppPrimaryButton>
      </div>
    </div>
  );
}

const sharedUsageFootnotePing = (
  <>
    Перед началом дальнейших действий дождитесь завершения тестов на всех серверах: это видно, когда у каждого сервера отобразится либо задержка (например, 123&nbsp;ms), либо n/a (сервер недоступен).
    Рекомендуется выбирать сервер с наименьшей задержкой, но это не всегда оптимально — например, если у сервера низкая скорость.
  </>
);

const sharedUsageFootnoteWhitelist = (
  <>
    Во время блокировок мобильного интернета работают только серверы, в имени которых есть Whitelist. Флаг таких серверов белый. В остальное время подходят любые серверы.
  </>
);

const sharedUsageFootnoteWhitelistDesktop = (
  <>
    Во время блокировок интернета работают только серверы, в имени которых есть Whitelist. Флаг таких серверов белый. В остальное время подходят любые серверы.
  </>
);

function IosBody() {
  return (
    <div className="space-y-8 text-[var(--foreground)]">
      <section className="space-y-4">
        <h3 className="text-base font-semibold text-[var(--foreground)]">Установка</h3>
        <ol className="list-decimal pl-5 space-y-4">
          <li className="space-y-3">
            <p>Установите приложение Happ, если ещё не установлено.</p>
            <HappDownloadButton
              href="https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973"
              sourceCaption="Версия с App Store"
            >
              Скачать Happ
            </HappDownloadButton>
            <Note>
              Если приложение уже было установлено, удалите иные подписки перед выполнением дальнейших шагов.
            </Note>
            <ImgPlaceholder />
          </li>
          <li>
            В меню сайта выберите «Настройки VPN» и нажмите «Сгенерировать ссылку».
            <ImgPlaceholder />
          </li>
          <li>
            Нажмите на ссылку и при необходимости подтвердите переход в приложение Happ.
            <ImgPlaceholder />
          </li>
        </ol>
      </section>

      <section className="space-y-4">
        <h3 className="text-base font-semibold text-[var(--foreground)]">Использование</h3>
        <ol className="list-decimal pl-5 space-y-4">
          <li>
            Раскройте выпадающий список подписки.
            <ImgPlaceholder />
          </li>
          <li className="space-y-3">
            <p>
              <span className="font-medium">2.1.</span> Перед использованием рекомендуется измерить ping до серверов,
              нажав соответствующую кнопку (см. изображение).
            </p>
            <Note>{sharedUsageFootnotePing}</Note>
            <ImgPlaceholder />
            <p>
              <span className="font-medium">2.2.</span> Нажмите подходящий сервер, затем большую кнопку запуска VPN.
            </p>
            <Note>{sharedUsageFootnoteWhitelist}</Note>
            <ImgPlaceholder />
          </li>
          <li className="space-y-3">
            <p>
              Для лучшего опыта не пропускайте следующие шаги: настройка «Обход» для российских приложений.
            </p>
            <p>
              <span className="font-medium">3.1.</span> Чтобы VPN не мешал российским приложениям, нажмите кнопку
              настроек.
            </p>
            <ImgPlaceholder />
            <p>
              <span className="font-medium">3.2.</span> В настройках выберите «Прокси для выбранных приложений».
            </p>
            <ImgPlaceholder />
            <p>
              <span className="font-medium">3.3.</span> Откройте вкладку «Обход» и отметьте российские приложения
              (особенно те, что работают во время блокировок; остальные можно не трогать).
            </p>
            <ImgPlaceholder />
            <p>
              <span className="font-medium">3.4.</span> Закройте настройки — больше они не понадобятся. Приятного
              пользования.
            </p>
          </li>
        </ol>
      </section>
    </div>
  );
}

function AndroidBody() {
  return (
    <div className="space-y-8 text-[var(--foreground)]">
      <section className="space-y-4">
        <h3 className="text-base font-semibold text-[var(--foreground)]">Установка</h3>
        <ol className="list-decimal pl-5 space-y-4">
          <li className="space-y-3">
            <p>Установите приложение Happ, если ещё не установлено.</p>
            <HappDownloadButton
              href="https://play.google.com/store/apps/details?id=com.happproxy&hl=ru"
              sourceCaption="Версия с Google Play"
            >
              Скачать Happ
            </HappDownloadButton>
            <Note>
              Если приложение уже было установлено, удалите иные подписки перед выполнением дальнейших шагов.
            </Note>
            <ImgPlaceholder />
          </li>
          <li>
            В меню сайта выберите «Настройки VPN» и нажмите «Сгенерировать ссылку».
            <ImgPlaceholder />
          </li>
          <li>
            Нажмите на ссылку и при необходимости подтвердите переход в приложение Happ.
            <ImgPlaceholder />
          </li>
        </ol>
      </section>

      <section className="space-y-4">
        <h3 className="text-base font-semibold text-[var(--foreground)]">Использование</h3>
        <ol className="list-decimal pl-5 space-y-4">
          <li>
            Раскройте выпадающий список подписки.
            <ImgPlaceholder />
          </li>
          <li className="space-y-3">
            <p>
              <span className="font-medium">2.1.</span> Перед использованием рекомендуется измерить ping до серверов,
              нажав соответствующую кнопку (см. изображение).
            </p>
            <Note>{sharedUsageFootnotePing}</Note>
            <ImgPlaceholder />
            <p>
              <span className="font-medium">2.2.</span> Нажмите подходящий сервер, затем большую кнопку запуска VPN.
            </p>
            <Note>{sharedUsageFootnoteWhitelist}</Note>
            <ImgPlaceholder />
          </li>
          <li className="space-y-3">
            <p>
              Для лучшего опыта не пропускайте следующие шаги: настройка «Обход» для российских приложений.
            </p>
            <p>
              <span className="font-medium">3.1.</span> Чтобы VPN не мешал российским приложениям, нажмите кнопку
              настроек.
            </p>
            <ImgPlaceholder />
            <p>
              <span className="font-medium">3.2.</span> В настройках выберите «Прокси для выбранных приложений».
            </p>
            <ImgPlaceholder />
            <p>
              <span className="font-medium">3.3.</span> Откройте вкладку «Обход» и отметьте российские приложения
              (особенно те, что работают во время блокировок; остальные можно не трогать).
            </p>
            <ImgPlaceholder />
            <p>
              <span className="font-medium">3.4.</span> Закройте настройки — больше они не понадобятся. Приятного
              пользования.
            </p>
          </li>
        </ol>
      </section>
    </div>
  );
}

function WindowsBody() {
  return (
    <div className="space-y-8 text-[var(--foreground)]">
      <section className="space-y-4">
        <h3 className="text-base font-semibold text-[var(--foreground)]">Установка</h3>
        <ol className="list-decimal pl-5 space-y-4">
          <li className="space-y-3">
            <p>Установите приложение Happ, если ещё не установлено.</p>
            <HappDownloadButton
              href="https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe"
              sourceCaption="Версия с GitHub"
            >
              Скачать Happ
            </HappDownloadButton>
            <Note>
              Если приложение уже было установлено, удалите иные подписки перед выполнением дальнейших шагов.
            </Note>
            <ImgPlaceholder />
          </li>
          <li>
            В меню сайта выберите «Настройки VPN» и нажмите «Сгенерировать ссылку».
            <ImgPlaceholder />
          </li>
          <li>
            Нажмите на ссылку и при необходимости подтвердите переход в приложение Happ.
            <ImgPlaceholder />
          </li>
        </ol>
      </section>

      <section className="space-y-4">
        <h3 className="text-base font-semibold text-[var(--foreground)]">Использование</h3>
        <ol className="list-decimal pl-5 space-y-4">
          <li>
            Раскройте выпадающий список подписки.
            <ImgPlaceholder />
          </li>
          <li className="space-y-3">
            <p>
              <span className="font-medium">2.1.</span> Перед использованием рекомендуется измерить ping до серверов,
              нажав соответствующую кнопку (см. изображение).
            </p>
            <Note>{sharedUsageFootnotePing}</Note>
            <ImgPlaceholder />
            <p>
              <span className="font-medium">2.2.</span> Нажмите подходящий сервер, затем большую кнопку запуска VPN.
            </p>
            <Note>{sharedUsageFootnoteWhitelistDesktop}</Note>
            <ImgPlaceholder />
          </li>
          <li className="space-y-3">
            <p>
              Для лучшего опыта не пропускайте следующие шаги: настройка «Обход» для российских приложений.
            </p>
            <p>
              <span className="font-medium">3.1.</span> Чтобы VPN не мешал российским приложениям, нажмите кнопку
              настроек.
            </p>
            <ImgPlaceholder />
            <p>
              <span className="font-medium">3.2.</span> В настройках выберите «Прокси для выбранных приложений».
            </p>
            <ImgPlaceholder />
            <p>
              <span className="font-medium">3.3.</span> Откройте вкладку «Обход» и отметьте российские приложения
              (особенно те, что работают во время блокировок; остальные можно не трогать).
            </p>
            <ImgPlaceholder />
            <p>
              <span className="font-medium">3.4.</span> Закройте настройки — больше они не понадобятся. Приятного
              пользования.
            </p>
          </li>
        </ol>
      </section>
    </div>
  );
}

const INSTRUCTION_ITEMS: InstructionItem[] = [
  {
    id: 'ios',
    title: 'Установка и использование VPN на iOS',
    content: <IosBody />,
  },
  {
    id: 'android',
    title: 'Установка и использование VPN на Android',
    content: <AndroidBody />,
  },
  {
    id: 'windows',
    title: 'Установка и использование VPN на Windows',
    content: <WindowsBody />,
  },
  {
    id: 'troubleshoot',
    title: 'Решение проблем с подключением',
    content: (
      <p className="text-[var(--foreground)]">
        В случае возникновения каких-либо проблем обращайтесь в поддержку.
      </p>
    ),
  },
];

export function Instructions() {
  return (
    <div className="h-full p-6 lg:p-8">
      <div className="max-w-3xl mx-auto space-y-6">
        <h1>Инструкции</h1>

        <Accordion.Root type="single" collapsible className="space-y-3">
          {INSTRUCTION_ITEMS.map((item) => (
            <Accordion.Item
              key={item.id}
              value={item.id}
              className="bg-[var(--accordion-bg)] rounded-lg overflow-hidden"
            >
              <Accordion.Header>
                <Accordion.Trigger className="w-full flex items-center justify-between px-4 py-4 text-left hover:opacity-80 transition-opacity duration-300 group">
                  <span className="font-semibold">{item.title}</span>
                  <FeatherIcon
                    name="chevron-down"
                    size={20}
                    className="shrink-0 text-[var(--accordion-indicator)] transition-transform duration-300 group-data-[state=open]:rotate-180"
                  />
                </Accordion.Trigger>
              </Accordion.Header>
              <Accordion.Content className="overflow-hidden data-[state=open]:animate-accordion-down data-[state=closed]:animate-accordion-up">
                <div className="px-4 pb-4 text-[var(--muted-foreground)] max-w-none [&_a]:text-[var(--foreground)]">
                  {item.content}
                </div>
              </Accordion.Content>
            </Accordion.Item>
          ))}
        </Accordion.Root>
      </div>
    </div>
  );
}
