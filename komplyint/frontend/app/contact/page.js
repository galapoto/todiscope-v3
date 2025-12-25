import Container from "@/components/ui/Container";
import Section from "@/components/ui/Section";
import { getLanguage, getTranslations } from "@/lib/translations";

export const metadata = {
  title: "Contact — KOMPLYINT",
  description: "Contact KOMPLYINT OY to discuss compliance readiness and preparation support.",
};

export default function ContactPage({ searchParams }) {
  const lang = getLanguage(searchParams);
  const t = getTranslations(lang);

  return (
    <Section>
      <Container>
        <div className="mx-auto max-w-2xl">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
            {t.contact.title}
          </h1>
          <p className="mt-6 text-lg text-slate-700">
            {t.contact.text}
          </p>
          <p className="mt-6">
            <a
              href="mailto:komplyint@komplying.com"
              className="text-lg font-medium text-blue-600 hover:text-blue-700 underline"
            >
              {t.contact.email}
            </a>
          </p>
          <p className="mt-6 text-sm text-slate-500">
            {t.contact.disclaimer}
          </p>
        </div>
      </Container>
    </Section>
  );
}
