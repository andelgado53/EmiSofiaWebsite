# Requirements Document

## Introduction

This feature extends the existing "Emi's Art", "Emi's Big Moments", and "Family Trips" sections to support video uploads alongside the existing photo upload functionality. Currently, media in these sections is limited to JPEG and PNG images uploaded via presigned S3 URLs and served through CloudFront. This feature adds support for uploading, storing, and displaying video files using the same S3/CloudFront infrastructure.

## Glossary

- **CMS**: The authenticated content management interface used by the site administrator to create and manage content
- **Media_Item**: A photo or video file associated with an Art piece, Moment, or Trip
- **Presign_Endpoint**: The backend API endpoint that generates presigned S3 upload URLs for client-side direct uploads
- **Video_File**: A media file with content type video/mp4 or video/webm
- **Photo_File**: A media file with content type image/jpeg or image/png
- **Media_Type**: A field indicating whether a Media_Item is a "photo" or "video"
- **Thumbnail**: A preview image representing a video in gallery views and list views
- **Upload_Component**: The frontend React component responsible for selecting, validating, and uploading media files

## Requirements

### Requirement 1: Video Presigned URL Generation

**User Story:** As a site administrator, I want to obtain presigned S3 upload URLs for video files, so that I can upload videos directly to S3 from the browser.

#### Acceptance Criteria

1. WHEN an authenticated presign request is received with content_type "video/mp4", THE Presign_Endpoint SHALL generate a presigned S3 PUT URL valid for 900 seconds and return it with the corresponding s3_key and cdn_url
2. WHEN an authenticated presign request is received with content_type "video/webm", THE Presign_Endpoint SHALL generate a presigned S3 PUT URL valid for 900 seconds and return it with the corresponding s3_key and cdn_url
3. THE Presign_Endpoint SHALL store video files under the S3 key pattern "videos/{year}/{uuid}.{ext}" where year is the current UTC year, uuid is a unique UUID4 identifier, and ext is "mp4" for video/mp4 or "webm" for video/webm
4. IF a presign request is received with a content_type other than "video/mp4" or "video/webm", THEN THE Presign_Endpoint SHALL return HTTP 400 with an error message indicating the list of accepted content types
5. IF a presign request is received without valid authentication, THEN THE Presign_Endpoint SHALL return HTTP 401 and SHALL NOT generate a presigned URL

### Requirement 2: Video File Size Validation

**User Story:** As a site administrator, I want the system to enforce a maximum video file size, so that storage costs remain manageable and uploads complete reliably.

#### Acceptance Criteria

1. WHEN a video file exceeding 100 MB is selected for upload, THE Upload_Component SHALL reject the file before requesting a presigned URL and display an error message indicating the maximum allowed size is 100 MB
2. WHEN a photo file exceeding 10 MB is selected for upload, THE Upload_Component SHALL reject the file before requesting a presigned URL and display an error message indicating the maximum allowed size is 10 MB
3. THE Upload_Component SHALL validate file size on the client side before requesting a presigned URL, ensuring no network request is made for oversized files
4. IF a selected file is 0 bytes, THEN THE Upload_Component SHALL reject the file and display an error message indicating the file is empty

### Requirement 3: Database Schema for Video Support

**User Story:** As a site administrator, I want videos stored with a media type indicator, so that the frontend can render photos and videos with appropriate players.

#### Acceptance Criteria

1. THE MomentPhoto model SHALL include a non-nullable media_type column of type String that stores exactly one of the values "photo" or "video"
2. THE TripPhoto model SHALL include a non-nullable media_type column of type String that stores exactly one of the values "photo" or "video"
3. THE ArtPiece model SHALL include a non-nullable media_type column of type String that stores exactly one of the values "photo" or "video"
4. WHEN a media_type value is not provided during record creation, THE database SHALL default the column to "photo"
5. THE database migration SHALL preserve all existing rows unchanged, with the media_type column set to "photo" for every pre-existing record
6. IF a value other than "photo" or "video" is provided for media_type, THEN THE system SHALL reject the input with a validation error indicating the allowed values

### Requirement 4: CMS Video Upload in Moments

**User Story:** As a site administrator, I want to upload videos when creating or editing a Moment, so that I can share video memories in the Big Moments section.

#### Acceptance Criteria

1. WHEN creating a Moment, THE CMS SHALL accept media items in the photos list where each item includes a media_type field with a value of either "photo" or "video"
2. WHEN updating a Moment, THE CMS SHALL accept media items in the photos list where each item includes a media_type field with a value of either "photo" or "video"
3. IF a media item is submitted with a media_type value other than "photo" or "video", THEN THE CMS SHALL reject the request with a validation error indicating the invalid media type
4. WHEN a Moment is deleted, THE CMS SHALL attempt to delete all associated S3 objects (both photo and video) and log any individual deletion failures without failing the overall delete operation
5. WHEN media items are removed during a Moment update, THE CMS SHALL attempt to delete the removed S3 objects (both photo and video) and log any individual deletion failures without failing the overall update operation

### Requirement 5: CMS Video Upload in Trips

**User Story:** As a site administrator, I want to upload videos when creating or editing a Trip, so that I can include video content in the Family Trips section.

#### Acceptance Criteria

1. WHEN creating a Trip, THE CMS SHALL accept media items in the photos list where each item includes a media_type field with a value of either "photo" or "video"
2. WHEN updating a Trip, THE CMS SHALL accept media items in the photos list where each item includes a media_type field with a value of either "photo" or "video"
3. IF a media item is submitted with a media_type value other than "photo" or "video", THEN THE CMS SHALL reject the request with a validation error indicating the invalid media type
4. WHEN a Trip is deleted, THE CMS SHALL attempt to delete all associated S3 objects (both photo and video) and continue processing even if individual S3 deletions fail
5. WHEN media items are removed during a Trip update, THE CMS SHALL attempt to delete the removed S3 objects (both photo and video) and continue processing even if individual S3 deletions fail
6. WHEN a Trip is retrieved via the CMS detail endpoint, THE CMS SHALL return the media_type field for each item in the photos list

### Requirement 6: CMS Video Upload in Art

**User Story:** As a site administrator, I want to upload video art pieces, so that I can showcase Emi's video artwork alongside her image artwork.

#### Acceptance Criteria

1. WHEN creating an Art piece, THE CMS SHALL accept an optional media_type field restricted to the values "photo" or "video", defaulting to "photo" when not provided
2. IF the media_type field contains a value other than "photo" or "video", THEN THE CMS SHALL reject the request with a validation error indicating the allowed values
3. THE CMS Art creation endpoint SHALL store the media_type value in the ArtPiece record and include it in the response body
4. WHEN an Art piece is deleted, THE CMS SHALL delete the associated S3 object on a best-effort basis regardless of media_type

### Requirement 7: Frontend Upload Component Video Support

**User Story:** As a site administrator, I want the upload component to accept video files alongside photos, so that I can add videos through the same familiar interface.

#### Acceptance Criteria

1. THE Upload_Component SHALL accept files with content type video/mp4 and video/webm in addition to image/jpeg and image/png, with a maximum file size of 100 MB per video file
2. THE Upload_Component SHALL display a video icon overlay on video file thumbnails in the media grid to visually distinguish them from photo thumbnails
3. IF the browser MIME type is empty or undefined for a selected file, THEN THE Upload_Component SHALL determine the content_type from the file extension, mapping .mp4 to video/mp4 and .webm to video/webm
4. THE Upload_Component SHALL display video files in the media grid using a static placeholder thumbnail that includes the video icon overlay
5. IF the user selects a file that is not image/jpeg, image/png, video/mp4, or video/webm (by content type or file extension), THEN THE Upload_Component SHALL reject the file and display an error message indicating the accepted file types

### Requirement 8: Public Video Playback in Moments

**User Story:** As a site visitor, I want to watch videos embedded in Moment pages, so that I can experience the full memory.

#### Acceptance Criteria

1. WHEN a Moment detail page contains media items with media_type "video", THE public Moments page SHALL render an HTML video player for each video item, using the item's cdn_url as the video source
2. THE video player SHALL provide visible play, pause, and volume controls, and SHALL NOT autoplay
3. THE public Moments API SHALL include the media_type field in the response for each media item, with allowed values limited to "photo" and "video"
4. IF a video media item fails to load, THEN THE video player SHALL display a static fallback message indicating the video is unavailable

### Requirement 9: Public Video Playback in Trips

**User Story:** As a site visitor, I want to watch videos embedded in Trip pages, so that I can see the trip videos alongside photos.

#### Acceptance Criteria

1. WHEN a Trip detail page contains media items with media_type "video", THE public Trips page SHALL render an HTML video player for each video item, using the item's cdn_url as the video source
2. THE video player SHALL provide visible play, pause, and volume controls, and SHALL NOT autoplay
3. THE public Trips API SHALL include the media_type field in the response for each media item, with allowed values limited to "photo" and "video"
4. IF a video media item fails to load, THEN THE video player SHALL display a static fallback message indicating the video is unavailable

### Requirement 10: Public Video Playback in Art

**User Story:** As a site visitor, I want to watch video art pieces on the Art gallery page, so that I can view Emi's video artwork.

#### Acceptance Criteria

1. WHEN an Art piece has media_type "video", THE public Art gallery page SHALL render an HTML video element instead of an image element for that piece
2. THE video player SHALL provide native browser play, pause, and volume controls and SHALL NOT autoplay
3. THE public Art API SHALL include the media_type field in the response for each art piece, with a value of either "photo" or "video"
4. IF a video art piece fails to load, THEN THE public Art gallery page SHALL display a static placeholder indicating the video is unavailable
5. THE video player SHALL be keyboard-accessible, allowing play and pause via standard keyboard interaction

### Requirement 11: Database Migration

**User Story:** As a developer, I want a safe Alembic migration that adds video support columns, so that the schema change is reversible and preserves existing data.

#### Acceptance Criteria

1. THE Alembic migration SHALL add a media_type column of type String(10) with NOT NULL constraint and server_default value "photo" to the moment_photos table
2. THE Alembic migration SHALL add a media_type column of type String(10) with NOT NULL constraint and server_default value "photo" to the trip_photos table
3. THE Alembic migration SHALL add a media_type column of type String(10) with NOT NULL constraint and server_default value "photo" to the art_pieces table
4. THE Alembic migration SHALL include a downgrade function that removes the media_type column from moment_photos, trip_photos, and art_pieces without modifying or deleting any other columns or row data in those tables
5. WHEN the migration is applied to an existing database containing rows in moment_photos, trip_photos, or art_pieces, THE migration SHALL set media_type to "photo" for all existing rows via the server_default so that no rows contain NULL in the media_type column
6. THE Alembic migration SHALL declare the previous migration revision as its down_revision to maintain a linear migration chain
