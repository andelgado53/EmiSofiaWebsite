# Requirements Document

## Introduction

"Notes for Emi" is a section of a personal website where a father writes notes addressed to his daughter, Emi. Notes range from a single sentence to a full essay and may cover any subject — life lessons, important ideas, or personal reflections that help Emi understand who her dad is. Each note can include up to two photos and one or more labels (tags) for future organization. The author publishes notes once or twice a week. The website currently runs as a static HTML file on AWS S3 + CloudFront, but the infrastructure is open to improvement to support this new section.

## Glossary

- **Website**: The personal website that contains the "Notes for Emi" section and potentially other sections.
- **Note**: A piece of writing authored by the father, directed to Emi, ranging from one sentence to a full essay.
- **Author**: The father who creates and publishes notes.
- **Emi**: The daughter who reads the notes; the intended audience.
- **Label**: A short text tag attached to a note for categorization and future search use.
- **Photo**: An image file (JPEG or PNG) attached to a note, limited to two per note.
- **Note_List**: The view that displays all published notes, ordered from newest to oldest.
- **Note_Detail**: The view that displays the full content of a single note, including its photos and labels.
- **CMS**: Content Management System — the interface the Author uses to create, edit, and publish notes.
- **Storage**: The backend service responsible for persisting notes, photos, and labels.

---

## Requirements

### Requirement 1: Display Notes for Emi Section

**User Story:** As Emi (or any visitor), I want to see a dedicated "Notes for Emi" section on the website, so that I can find and read all the notes my dad has written for me.

#### Acceptance Criteria

1. THE Website SHALL include a "Notes for Emi" section accessible via a visible, clickable link in the main navigation bar present on every page.
2. WHEN a visitor navigates to the "Notes for Emi" section, THE Note_List SHALL display all published notes (those whose publication date is on or before the current date) ordered from newest to oldest; WHEN two notes share the same publication date, THE Note_List SHALL order them by the time they were published, newest first.
3. WHEN the Note_List contains no published notes, THE Note_List SHALL display a message indicating that no notes are available yet.
4. WHEN the Note_List is displayed, THE Note_List SHALL show each note's title, publication date, a short excerpt (up to the first 200 characters of the body, or the full body if shorter), and, IF the note has one or more labels, all labels attached to it.
5. WHEN a visitor selects a note from the Note_List, THE Note_Detail SHALL display the note's full content and publication date; IF the note has one or more photos, THE Note_Detail SHALL display all attached photos; IF the note has one or more labels, THE Note_Detail SHALL display all labels.

---

### Requirement 2: Note Content

**User Story:** As the Author, I want to write notes of any length and on any subject, so that I can share thoughts, lessons, and personal reflections with Emi.

#### Acceptance Criteria

1. THE Note SHALL contain a title of 1 to 100 characters, a body, a publication date, zero to 10 labels each of 1 to 50 characters, and zero to two photos.
2. THE Note body SHALL support a minimum length of 1 character and a maximum length of 50,000 characters.
3. THE Note_Detail SHALL render the note body preserving paragraph breaks and the following text formatting: bold, italic, up to three heading levels, unordered lists, and ordered lists.
4. THE Note_Detail SHALL display only photos that have a non-empty image file attached, rendered inline within the note body.
5. THE Note_Detail SHALL NOT render placeholder slots for photos that have no image file attached.
6. IF the Author attempts to save a Note body exceeding 50,000 characters, THEN THE Note editor SHALL reject the save and display an error message indicating the character limit has been exceeded, without discarding the entered content.

---

### Requirement 3: Photo Attachments

**User Story:** As the Author, I want to attach one or two photos to a note, so that I can add visual context to what I'm writing.

#### Acceptance Criteria

1. THE CMS SHALL allow the Author to attach a minimum of zero and a maximum of two photos per note.
2. WHEN the Author attaches a photo, THE CMS SHALL accept only JPEG and PNG image files up to 10 MB each.
3. WHEN a note has one or two photos, THE Note_Detail SHALL display each photo inline within the note content, floated so that text wraps around it, in the order they were attached.
4. IF the Author attempts to attach more than two photos to a single note, THEN THE CMS SHALL reject the additional photo and display a message stating that a maximum of two photos is allowed per note.
5. IF an attached photo file exceeds 10 MB, THEN THE CMS SHALL reject the file and display a message stating the 10 MB per-file size limit.
6. IF the Author attempts to attach a file that is not a JPEG or PNG, THEN THE CMS SHALL reject the file and display a message stating that only JPEG and PNG files are accepted.

---

### Requirement 4: Labels (Tags)

**User Story:** As the Author, I want to add labels to each note, so that notes can be categorized and organized for future use.

#### Acceptance Criteria

1. WHEN creating a note, THE CMS SHALL allow the Author to add up to 20 labels to the note.
2. WHEN editing a note, THE CMS SHALL allow the Author to add labels up to the 20-label maximum.
3. IF the Author attempts to add a label that is empty or exceeds 50 characters, THEN THE CMS SHALL reject the label and display an error message indicating the valid label length (1 to 50 characters).
4. WHEN a note is displayed in the Note_List or Note_Detail, THE Website SHALL render all labels associated with that note as visible text.
5. THE CMS SHALL allow the Author to remove a label from a note before or after publishing.
6. IF the Author attempts to add a label that already exists on the note (case-insensitive), THEN THE CMS SHALL deduplicate and retain only one instance of that label.

---

### Requirement 5: Authoring and Publishing Notes

**User Story:** As the Author, I want a simple way to create and publish notes, so that I can add new content once or twice a week without technical friction.

#### Acceptance Criteria

1. THE CMS SHALL provide a form where the Author can enter a title (up to 200 characters), a body (up to 50,000 characters), up to 20 labels, and up to 2 photos for a new note.
2. THE CMS SHALL allow the Author to save a note as a draft before publishing it.
3. IF the Author attempts to publish or republish a note with an empty title, THEN THE CMS SHALL reject the action and display an error message requiring a title.
4. WHEN the Author publishes a note, THE Storage SHALL persist the note and THE Note_List SHALL include the new note within 60 seconds; IF the publish operation cannot complete within 60 seconds, THEN THE CMS SHALL abort the operation, retain the note as a draft, and display an error message to the Author.
5. THE CMS SHALL allow the Author to edit a previously published note.
6. WHEN the Author edits and republishes a note, THE Note_Detail SHALL reflect the updated content within 60 seconds; IF the republish operation cannot complete within 60 seconds, THEN THE CMS SHALL abort the operation and display an error message to the Author.
7. THE CMS SHALL allow the Author to delete a note.
8. WHEN the Author deletes a note, THE Note_List SHALL no longer display the deleted note within 60 seconds; IF the delete operation fails, THEN THE CMS SHALL display an error message and retain the note.

---

### Requirement 6: Infrastructure and Hosting

**User Story:** As the Author, I want the website self-hosted on my own infrastructure, so that I have full control over the deployment and can keep costs low.

#### Acceptance Criteria

1. THE Website SHALL be served over HTTPS at the domain emisofia.com.
2. THE Website SHALL be accessible via emisofia.com without requiring Emi to log in or authenticate.
3. WHEN a visitor loads the Note_List page, THE Website SHALL return the page within 3 seconds under normal network conditions.
4. THE application and CMS SHALL be hosted on the Author's Oracle Cloud VM instance.
5. THE Storage SHALL use AWS S3 to persist note photos durably, with no data loss under normal operating conditions.
6. WHEN a photo is displayed in the Note_Detail, THE Website SHALL serve the photo via AWS CloudFront (CDN) to ensure fast delivery.
7. THE Website SHALL not require the Author to manually edit HTML files to publish a new note.
8. THE CMS SHALL be protected so that only the Author can create, edit, or delete notes (e.g., via password or authentication).
9. THE Oracle VM SHALL run a reverse proxy (e.g., Nginx) to terminate HTTPS and forward requests to the application server.
