import Container from "@/components/ui/Container";
import Section from "@/components/ui/Section";
import { getLanguage, getTranslations } from "@/lib/translations";

export const metadata = {
  title: "Privacy — KOMPLYINT",
  description: "Privacy policy for KOMPLYINT OY. Information about data collection and privacy practices.",
};

export default function PrivacyPage({ searchParams }) {
  const lang = getLanguage(searchParams);
  const t = getTranslations(lang);

  return (
    <Section>
      <Container>
        <div className="mx-auto max-w-3xl">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
            {t.privacy.title}
          </h1>
          <div className="mt-8 space-y-4 text-slate-700">
            {t.privacy.content.map((paragraph, index) => (
              <p key={index} className="leading-relaxed">
                {paragraph}
              </p>
            ))}
          </div>
        </div>
      </Container>
    </Section>
  );
}
