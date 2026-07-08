export default function RadioGroup({ legend, name, options, value, onChange, required = false }) {
  return (
    <fieldset className="radio-group">
      <legend>{legend}</legend>
      <div className="radio-options">
        {options.map((option) => (
          <label className="radio-option" key={option.value}>
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={(event) => onChange(event.target.value)}
              required={required}
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
