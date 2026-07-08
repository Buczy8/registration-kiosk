import { useFormContext } from "react-hook-form";

import { collectFormErrorMessages } from "../../lib/registrationFormShared.js";

export default function FormValidationSummary() {
  const {
    formState: { errors, submitCount },
  } = useFormContext();

  if (!submitCount) {
    return null;
  }

  const messages = collectFormErrorMessages(errors);
  if (!messages.length) {
    return null;
  }

  return (
    <div className="alert" role="alert">
      <p>Błędy walidacji:</p>
      <ul>
        {messages.map((error) => (
          <li key={error}>{error}</li>
        ))}
      </ul>
    </div>
  );
}
