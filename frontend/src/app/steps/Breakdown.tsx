import type { BreakdownResponse } from '@/api/schemas';
import { useI18n } from '@/i18n';
import { componentLabel } from '@/i18n/labels';
import type { Translator } from '@/i18n';

type Component = BreakdownResponse['components'][number];

function formatNumber(value: number | null): string {
  return value === null ? '—' : value.toFixed(2);
}

function axisNoteLabel(note: string, t: Translator): string {
  if (note === 'combined') {
    return t('breakdown.axisNote.combined');
  }
  if (note.startsWith('capacity axis unavailable')) {
    return t('breakdown.axisNote.characterOnly');
  }
  return note;
}

function AxisTable({
  axis,
  components,
  t,
}: {
  axis: 'character' | 'capacity';
  components: Component[];
  t: Translator;
}) {
  if (components.length === 0) {
    return null;
  }
  return (
    <div className="breakdown-axis">
      <h3>{axis === 'character' ? t('breakdown.character') : t('breakdown.capacity')}</h3>
      <table>
        <thead>
          <tr>
            <th scope="col">{t('breakdown.signal')}</th>
            <th scope="col">{t('breakdown.value')}</th>
            <th scope="col">{t('breakdown.contribution')}</th>
            <th scope="col">{t('breakdown.weight')}</th>
          </tr>
        </thead>
        <tbody>
          {components.map((component, index) => (
            <tr key={`${component.axis}-${component.component_name}-${index}`} data-testid="breakdown-row">
              <td>{componentLabel(component.component_name, t)}</td>
              <td>{component.raw_value}</td>
              <td>{formatNumber(component.contribution)}</td>
              <td>{formatNumber(component.weight)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Breakdown({
  components,
  axisNote,
}: {
  components: Component[];
  axisNote: string;
}) {
  const { t } = useI18n();
  const character = components.filter((component) => component.axis === 'character');
  const capacity = components.filter((component) => component.axis === 'capacity');

  return (
    <section className="breakdown" aria-label={t('breakdown.aria')} data-testid="breakdown">
      <header>
        <h2>{t('breakdown.title')}</h2>
        <p>{axisNoteLabel(axisNote, t)}</p>
      </header>
      {components.length === 0 ? (
        <p className="case-status">{t('breakdown.empty')}</p>
      ) : (
        <>
          <AxisTable axis="character" components={character} t={t} />
          <AxisTable axis="capacity" components={capacity} t={t} />
        </>
      )}
    </section>
  );
}
