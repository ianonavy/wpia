from db import app
from flask.ext.uploads import UploadSet, configure_uploads, ARCHIVES, DOCUMENTS

PRESENTATIONS = ('ppt', 'pptx', 'odp')
PDF = ('pdf',)

print(app.config)

submissions = UploadSet('submissions', ARCHIVES)
presentations = UploadSet('presentations', PRESENTATIONS)
syllabi = UploadSet('syllabi', PDF)
assignment_descs = UploadSet('assignments', DOCUMENTS + PDF)

configure_uploads(app, (submissions, presentations, syllabi, assignment_descs))
