import type { IBSubject } from '@/types'

export const IB_SUBJECTS: IBSubject[] = [
  // Group 1 — Studies in Language and Literature
  { name: 'English A: Literature', group: 1, groupName: 'Language & Literature', availableHL: true, availableSL: true },
  { name: 'English A: Language & Literature', group: 1, groupName: 'Language & Literature', availableHL: true, availableSL: true },
  { name: 'English B', group: 2, groupName: 'Language Acquisition', availableHL: true, availableSL: true },

  // Group 2 — Language Acquisition
  { name: 'French B', group: 2, groupName: 'Language Acquisition', availableHL: true, availableSL: true },
  { name: 'Spanish B', group: 2, groupName: 'Language Acquisition', availableHL: true, availableSL: true },
  { name: 'Mandarin B', group: 2, groupName: 'Language Acquisition', availableHL: true, availableSL: true },
  { name: 'German B', group: 2, groupName: 'Language Acquisition', availableHL: true, availableSL: true },
  { name: 'Japanese B', group: 2, groupName: 'Language Acquisition', availableHL: true, availableSL: true },

  // Group 3 — Individuals and Societies
  { name: 'Economics', group: 3, groupName: 'Individuals & Societies', availableHL: true, availableSL: true },
  { name: 'History', group: 3, groupName: 'Individuals & Societies', availableHL: true, availableSL: true },
  { name: 'Geography', group: 3, groupName: 'Individuals & Societies', availableHL: true, availableSL: true },
  { name: 'Psychology', group: 3, groupName: 'Individuals & Societies', availableHL: true, availableSL: true },
  { name: 'Business Management', group: 3, groupName: 'Individuals & Societies', availableHL: true, availableSL: true },
  { name: 'Global Politics', group: 3, groupName: 'Individuals & Societies', availableHL: true, availableSL: true },
  { name: 'Philosophy', group: 3, groupName: 'Individuals & Societies', availableHL: true, availableSL: true },
  { name: 'Social & Cultural Anthropology', group: 3, groupName: 'Individuals & Societies', availableHL: true, availableSL: true },

  // Group 4 — Sciences
  { name: 'Biology', group: 4, groupName: 'Sciences', availableHL: true, availableSL: true },
  { name: 'Chemistry', group: 4, groupName: 'Sciences', availableHL: true, availableSL: true },
  { name: 'Physics', group: 4, groupName: 'Sciences', availableHL: true, availableSL: true },
  { name: 'Computer Science', group: 4, groupName: 'Sciences', availableHL: true, availableSL: true },
  { name: 'Environmental Systems & Societies', group: 4, groupName: 'Sciences', availableHL: false, availableSL: true },
  { name: 'Sports, Exercise & Health Science', group: 4, groupName: 'Sciences', availableHL: true, availableSL: true },
  { name: 'Design Technology', group: 4, groupName: 'Sciences', availableHL: true, availableSL: true },

  // Group 5 — Mathematics
  { name: 'Mathematics: Analysis & Approaches', group: 5, groupName: 'Mathematics', availableHL: true, availableSL: true },
  { name: 'Mathematics: Applications & Interpretation', group: 5, groupName: 'Mathematics', availableHL: true, availableSL: true },

  // Group 6 — The Arts
  { name: 'Visual Arts', group: 6, groupName: 'The Arts', availableHL: true, availableSL: true },
  { name: 'Music', group: 6, groupName: 'The Arts', availableHL: true, availableSL: true },
  { name: 'Theatre', group: 6, groupName: 'The Arts', availableHL: true, availableSL: true },
  { name: 'Film', group: 6, groupName: 'The Arts', availableHL: true, availableSL: true },
  { name: 'Dance', group: 6, groupName: 'The Arts', availableHL: true, availableSL: true },
]

export const GROUP_NAMES: Record<number, string> = {
  1: 'Language & Literature',
  2: 'Language Acquisition',
  3: 'Individuals & Societies',
  4: 'Sciences',
  5: 'Mathematics',
  6: 'The Arts',
}

export const SUBJECT_NAMES = IB_SUBJECTS.map(s => s.name)
