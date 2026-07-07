export default function FormValidationAlert({ errors }) {
  if (!errors?.length) {
    return null;
  }

  return (
    <div className="alert" role="alert">
      <p>Błędy walidacji:</p>
      <ul>
        {errors.map((error) => (
          <li key={error}>{error}</li>
        ))}
      </ul>
    </div>
  );
}
