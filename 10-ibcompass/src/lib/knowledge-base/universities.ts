import type { UniversityRequirement } from '@/types'

export const UNIVERSITY_REQUIREMENTS: UniversityRequirement[] = [
  // UK — Oxbridge
  { university: 'University of Oxford', country: 'UK', region: 'UK', requiresHL: [], minimumPoints: 38, notes: 'Course-specific HL requirements. Medicine requires Biology + Chemistry HL (minimum 7,6,6). Law requires no science. Admission test required for most courses (UCAT, LNAT, MAT, etc.).', competitivenessScore: 10 },
  { university: 'University of Cambridge', country: 'UK', region: 'UK', requiresHL: [], minimumPoints: 40, notes: 'Among the most demanding IB requirements globally. Minimum 40-42 points. Course-specific: Medicine 7,7,6; Engineering 7,7,6 (Maths+Physics+Chemistry); Economics 7,7,6.', competitivenessScore: 10 },

  // UK — Russell Group
  { university: 'Imperial College London', country: 'UK', region: 'UK', requiresHL: [], minimumPoints: 38, notes: 'STEM-focused. Engineering: Maths AA HL + Physics HL minimum 6,6. Medicine: Biology + Chemistry HL 6,6. Computer Science: Maths AA HL 7 expected.', competitivenessScore: 9 },
  { university: 'London School of Economics (LSE)', country: 'UK', region: 'UK', requiresHL: ['Mathematics: Analysis & Approaches'], minimumPoints: 37, notes: 'Maths AA HL required for Economics, Finance, Statistics courses. 38 points standard offer. Highly competitive for Economics and Finance.', competitivenessScore: 9 },
  { university: 'University College London (UCL)', country: 'UK', region: 'UK', requiresHL: [], minimumPoints: 36, notes: 'Requirements vary by faculty. Medicine: Biology + Chemistry HL. Law: 38+ points, LNAT required. Engineering: Maths + Physics HL.', competitivenessScore: 9 },
  { university: 'University of Edinburgh', country: 'UK', region: 'UK', requiresHL: [], minimumPoints: 34, notes: 'Strong for Medicine, Law, Engineering. Medicine: 36-38 points, Biology + Chemistry HL. Often slightly lower offer than London schools.', competitivenessScore: 8 },
  { university: 'University of Manchester', country: 'UK', region: 'UK', requiresHL: [], minimumPoints: 32, notes: 'Good entry point for Medicine (very competitive), Engineering, Law. Slightly lower offers than Oxbridge/London.', competitivenessScore: 7 },
  { university: "King's College London", country: 'UK', region: 'UK', requiresHL: [], minimumPoints: 35, notes: 'Strong for Medicine, Law, Business. Medicine: 36-38 points with Biology + Chemistry HL. Law: LNAT required.', competitivenessScore: 8 },

  // US — Ivy League
  { university: 'Harvard University', country: 'USA', region: 'North America', requiresHL: [], minimumPoints: 40, notes: 'No minimum IB score but accepted students typically score 40-45. Test-optional but strong scores help. Holistic admissions — ECs, essays, recommendations matter enormously.', competitivenessScore: 10 },
  { university: 'MIT', country: 'USA', region: 'North America', requiresHL: ['Mathematics: Analysis & Approaches'], minimumPoints: 40, notes: 'STEM-focused. Maths AA HL 7 and Physics/Chemistry/CS HL expected. 40+ IB points typical for admitted students. Research experience and projects highly valued.', competitivenessScore: 10 },
  { university: 'Princeton University', country: 'USA', region: 'North America', requiresHL: [], minimumPoints: 40, notes: 'Top 3 US university. Holistic admissions. Engineering applicants expected to have strong Maths + Science HL. 40+ IB typical.', competitivenessScore: 10 },
  { university: 'Yale University', country: 'USA', region: 'North America', requiresHL: [], minimumPoints: 39, notes: 'Strong humanities + science programs. 39-43 IB typical. Test-optional. Holistic — ECs and essays weighted heavily.', competitivenessScore: 10 },
  { university: 'University of Pennsylvania (Wharton)', country: 'USA', region: 'North America', requiresHL: ['Mathematics: Analysis & Approaches', 'Economics'], minimumPoints: 39, notes: 'Wharton (business) is world-renowned. Maths AA HL + Economics HL expected for finance/business. Very high acceptance bar.', competitivenessScore: 10 },
  { university: 'Columbia University', country: 'USA', region: 'North America', requiresHL: [], minimumPoints: 39, notes: 'Strong for pre-med, engineering, humanities. Core curriculum. NYC location. 39-43 IB typical.', competitivenessScore: 10 },

  // US — Top non-Ivy
  { university: 'Stanford University', country: 'USA', region: 'North America', requiresHL: [], minimumPoints: 40, notes: 'Arguably harder to get into than most Ivies. Tech and entrepreneurship culture. Research and projects matter enormously alongside academics.', competitivenessScore: 10 },
  { university: 'University of Chicago', country: 'USA', region: 'North America', requiresHL: ['Mathematics: Analysis & Approaches'], minimumPoints: 38, notes: 'Rigorous academic culture. Economics is world-class. Maths AA HL strongly preferred. Known for unconventional application essays.', competitivenessScore: 9 },
  { university: 'UC Berkeley', country: 'USA', region: 'North America', requiresHL: [], minimumPoints: 36, notes: 'Public university. Computer Science and Engineering among the best globally. CS: Maths AA HL + Physics/CS HL expected. State residents have advantage.', competitivenessScore: 8 },
  { university: 'New York University (NYU)', country: 'USA', region: 'North America', requiresHL: [], minimumPoints: 34, notes: 'Strong for Business (Stern), Law (pre-law), Film, Arts. More accessible than Ivies. NYC location a big draw.', competitivenessScore: 7 },

  // Canada
  { university: 'University of Toronto', country: 'Canada', region: 'North America', requiresHL: [], minimumPoints: 32, notes: 'Canada\'s top-ranked university. Medicine (highly competitive): Biology + Chemistry HL. Engineering: Maths + Physics HL. Generally lower bar than US/UK top schools.', competitivenessScore: 8 },
  { university: 'University of British Columbia (UBC)', country: 'Canada', region: 'North America', requiresHL: [], minimumPoints: 30, notes: 'Strong across most disciplines. Engineering and CS well-regarded. Generally accessible for strong IB students (30+ points with strong HLs).', competitivenessScore: 7 },
  { university: 'McGill University', country: 'Canada', region: 'North America', requiresHL: [], minimumPoints: 33, notes: 'Canada\'s most prestigious. Medicine: very competitive, Biology + Chemistry HL required. Law: 34+ points. Strong reputation internationally.', competitivenessScore: 8 },

  // Singapore
  { university: 'National University of Singapore (NUS)', country: 'Singapore', region: 'Asia', requiresHL: [], minimumPoints: 36, notes: 'Top Asian university. Medicine and Law highly competitive. Engineering: Maths + Physics HL. CS: Maths AA HL + CS HL. Scholarship opportunities for international students.', competitivenessScore: 9 },
  { university: 'Nanyang Technological University (NTU)', country: 'Singapore', region: 'Asia', requiresHL: [], minimumPoints: 34, notes: 'Strong for Engineering, Business, CS. Maths AA HL preferred for technical programs. Very competitive for international applicants.', competitivenessScore: 8 },

  // Australia
  { university: 'University of Melbourne', country: 'Australia', region: 'Oceania', requiresHL: [], minimumPoints: 33, notes: 'Australia\'s highest-ranked. Medicine uses graduate-entry model — undergraduate degree first. Engineering: Maths + Physics HL. Good value compared to UK/US.', competitivenessScore: 8 },
  { university: 'Australian National University (ANU)', country: 'Australia', region: 'Oceania', requiresHL: [], minimumPoints: 32, notes: 'Strong for international relations, law, sciences. Policy-focused. Good scholarship options for IB students.', competitivenessScore: 7 },
  { university: 'University of Sydney', country: 'Australia', region: 'Oceania', requiresHL: [], minimumPoints: 32, notes: 'Strong for Medicine, Law, Engineering. Graduate-entry medicine. Good for IB students targeting 32-36 points.', competitivenessScore: 7 },

  // Europe
  { university: 'ETH Zurich', country: 'Switzerland', region: 'Europe', requiresHL: ['Mathematics: Analysis & Approaches', 'Physics'], minimumPoints: 35, notes: 'Top European technical university. STEM-only. Maths AA HL 6-7 + Physics HL 6-7 essential. Entrance exam required. Instruction mostly in German/English.', competitivenessScore: 9 },
  { university: 'Delft University of Technology (TU Delft)', country: 'Netherlands', region: 'Europe', requiresHL: ['Mathematics: Analysis & Approaches'], minimumPoints: 30, notes: 'Europe\'s top engineering school. English-taught programs available. Maths AA HL + Physics HL for Engineering. Accessible for strong IB students.', competitivenessScore: 7 },
  { university: 'University of Amsterdam', country: 'Netherlands', region: 'Europe', requiresHL: [], minimumPoints: 28, notes: 'Strong English-language programs in Business, Social Sciences, Law. Very accessible for IB students. Economics programs well-regarded in Europe.', competitivenessScore: 6 },
]

export const COUNTRIES = [
  'UK',
  'USA',
  'Canada',
  'Singapore',
  'Australia',
  'Netherlands',
  'Switzerland',
  'Germany',
  'France',
  'Japan',
]

export const UNIVERSITIES_BY_COUNTRY = UNIVERSITY_REQUIREMENTS.reduce(
  (acc, uni) => {
    if (!acc[uni.country]) acc[uni.country] = []
    acc[uni.country].push(uni)
    return acc
  },
  {} as Record<string, UniversityRequirement[]>
)
