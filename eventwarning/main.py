import eventful
import unicodedata
import pprint
import danger_backend
from datetime import date

print "Today's danger: %i" % danger_backend.print_day_summary(date.today())
