// import React, { useState } from 'react';
//
// export default function RoleVehicleSelect({ onNavigate }) {
//   const [role, setRole] = useState('');
//
//   const [vehicle, setVehicle] = useState('');
//
//   const [error, setError] = useState('');
//
//   const handleNext = () => {
//     if (!role) {
//       setError('Proszę wybrać rolę uczestnika.');
//       return;
//     }
//     if (!vehicle) {
//       setError('Proszę wybrać rodzaj pojazdu.');
//       return;
//     }
//
//     setError('');
//
//     if (role === 'legal_guardian') {
//       onNavigate('placeholder_guardian', { role, vehicle });
//     } else {
//       onNavigate('verify_data_form', { role, vehicle });
//     }
//   };
//
//   return (
//     <div className="card" style={{ maxWidth: '600px', margin: '0 auto', padding: '20px' }}>
//       <h2>Wybierz swoją rolę i pojazd</h2>
//
//       {error && (
//         <div className="alert alert-danger" style={{ color: 'red', marginBottom: '15px' }}>
//           {error}
//         </div>
//       )}
//
//       <div className="form-group" style={{ marginBottom: '20px' }}>
//         <h3>Rola uczestnika:</h3>
//         <div style={{ display: 'flex', gap: '15px', flexDirection: 'column' }}>
//           <label>
//             <input
//               type="radio"
//               name="participant_role"
//               value="driver"
//               checked={role === 'driver'}
//               onChange={(e) => setRole(e.target.value)}
//             /> Kierowca
//           </label>
//           <label>
//             <input
//               type="radio"
//               name="participant_role"
//               value="passenger"
//               checked={role === 'passenger'}
//               onChange={(e) => setRole(e.target.value)}
//             /> Pasażer
//           </label>
//           <label>
//             <input
//               type="radio"
//               name="participant_role"
//               value="legal_guardian"
//               checked={role === 'legal_guardian'}
//               onChange={(e) => setRole(e.target.value)}
//             /> Opiekun prawny
//           </label>
//         </div>
//       </div>
//
//       <div className="form-group" style={{ marginBottom: '20px' }}>
//         <h3>Rodzaj pojazdu:</h3>
//         <div style={{ display: 'flex', gap: '15px', flexDirection: 'column' }}>
//           <label>
//             <input
//               type="radio"
//               name="vehicle_type"
//               value="car"
//               checked={vehicle === 'car'}
//               onChange={(e) => setVehicle(e.target.value)}
//             /> Samochód
//           </label>
//           <label>
//             <input
//               type="radio"
//               name="vehicle_type"
//               value="motorcycle"
//               checked={vehicle === 'motorcycle'}
//               onChange={(e) => setVehicle(e.target.value)}
//             /> Motocykl
//           </label>
//           <label>
//             <input
//               // type="radio"
//               name="vehicle_type"
//               value="gokart"
//               checked={vehicle === 'gokart'}
//               onChange={(e) => setVehicle(e.target.value)}
//             /> Gokart
//           </label>
//         </div>
//       </div>
//
//       <button
//         onClick={handleNext}
//         style={{ padding: '10px 20px', cursor: 'pointer', background: '#007bff', color: 'white', border: 'none', borderRadius: '4px' }}
//       >
//         Dalej
//       </button>
//     </div>
//   );
// }