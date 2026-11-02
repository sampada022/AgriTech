export const navLinks = [
  { label: 'Problem', href: '#problem' },
  { label: 'How it works', href: '#how' },
  { label: 'Technology', href: '#technology' },
  { label: 'Try it', href: '#try' },
  { label: 'Impact', href: '#impact' },
  { label: 'Team', href: '#team' },
]

export const stats = [
  { value: 10, suffix: '–15%', unit: '', display: '10–15%', label: 'annual global crop yield lost to pests', accent: true },
  { value: 300, suffix: 'M+', unit: 'tonnes', display: '300M+ tonnes', label: 'lost every year' },
  { value: 50, suffix: '', unit: 'acres', display: '50 acres', label: 'a scout walks blind to find a few patches' },
  { value: 0, suffix: '', unit: '', display: 'mm-scale', label: "insect detail a drone can't see from practical altitude", text: true },
]

export const compareCols = ['Catches small early patches', 'Separates pest from drought', 'Confirms the species', 'Fast enough to act']
export type Rating = 'yes' | 'partial' | 'no'
export const compareRows: { name: string; ratings: Rating[]; hero?: boolean }[] = [
  { name: 'Manual foot scouting', ratings: ['partial', 'partial', 'yes', 'no'] },
  { name: 'Drone RGB mapping', ratings: ['partial', 'no', 'no', 'yes'] },
  { name: 'Satellite remote sensing', ratings: ['no', 'no', 'no', 'partial'] },
  { name: 'AeroScout', ratings: ['yes', 'yes', 'yes', 'yes'], hero: true },
]

export const steps = [
  { n: '01', title: 'Scan & tile', body: 'The drone maps the field at 35 m. Each image is cut into small tiles (a method called SAHI) so small patches are not lost, and every tile gets a VARI score, a greenness number worked out from ordinary camera colours.', readout: 'ALT 35.0 M · VARI per tile' },
  { n: '02', title: 'Analyze', body: 'GLCM texture maths compares how rough or smooth each patch is. Ragged damage points to insects. An even fade points to drought. DBSCAN, a clustering method, groups the suspect pixels into hotspots.', readout: 'Abiotic dismissed · 3 hotspots' },
  { n: '03', title: 'Route', body: 'The app builds the shortest walking path that visits only the hotspots. The farmer follows it on a phone.', readout: '1.2 km instead of 50 acres' },
  { n: '04', title: 'Identify', body: 'At the hotspot, the farmer photographs a leaf. Species AI confirms the pest, and the photo is linked back to the aerial tile it came from.', readout: 'Fall armyworm · sample result' },
]

export const loop = ['Drone sees', 'Model flags', 'Farmer confirms', 'Model retrains']

export const impact = [
  { icon: 'users', title: 'Social', body: 'No more walking 50-acre fields blind. Farmers get a clear diagnosis report they can act on and show to others.' },
  { icon: 'coins', title: 'Economic', body: 'Lower spray costs, and outbreaks caught before they cut yield.' },
  { icon: 'sprout', title: 'Environmental', body: 'Less chemical runoff into soil and groundwater, and healthier soil microbiology.' },
] as const

export const team = [
  { name: 'Pushpa Nagashree S', role: 'Team lead', mono: 'PN' },
  { name: 'Chaithra M U', role: 'Team member', mono: 'CM' },
  { name: 'Sampada M B', role: 'Team member', mono: 'SM' },
]

export const tools = ['VARI', 'SAHI', 'GLCM', 'DBSCAN', 'YOLO', 'FastAPI', 'OpenCV', 'Next.js']
