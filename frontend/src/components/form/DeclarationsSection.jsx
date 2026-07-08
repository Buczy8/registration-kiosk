import { Controller, useFormContext } from "react-hook-form";

import DeclarationsPanel from "../DeclarationsPanel.jsx";

export default function DeclarationsSection({ legend = "IV. Oświadczenia oraz akceptacja ryzyka" }) {
  const { control, watch } = useFormContext();
  const declarationsReviewed = watch("declarationsReviewed");

  return (
    <fieldset className="form-card">
      <legend>{legend}</legend>
      <p className="hint">Zapoznaj się z pełną treścią poniżej. Przewiń tekst do końca przed wysłaniem.</p>
      <Controller
        control={control}
        name="declarationsReviewed"
        render={({ field }) => (
          <DeclarationsPanel reviewed={field.value} onReviewed={() => field.onChange(true)} />
        )}
      />
      {!declarationsReviewed && (
        <p className="review-hint">Przewiń oświadczenia do końca, aby wysłać formularz.</p>
      )}
    </fieldset>
  );
}
