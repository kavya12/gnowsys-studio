# Copyright (c) 2011,  2012 Free Software Foundation

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU Affero General Public License as
#     published by the Free Software Foundation, either version 3 of the
#     License, or (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.

#     You should have received a copy of the GNU Affero General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.


# This project incorporates work covered by the following copyright and permission notice:  

#    Copyright (c) 2009, Julien Fache
#    All rights reserved.

#    Redistribution and use in source and binary forms, with or without
#    modification, are permitted provided that the following conditions
#    are met:

#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in
#      the documentation and/or other materials provided with the
#      distribution.
#    * Neither the name of the author nor the names of other
#      contributors may be used to endorse or promote products derived
#      from this software without specific prior written permission.

#    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#    "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#    LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
#    FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
#    COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
#    INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#    SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
#    HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
#    STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
#    OF THE POSSIBILITY OF SUCH DAMAGE.

# Copyright (c) 2011,  2012 Free Software Foundation

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU Affero General Public License as
#     published by the Free Software Foundation, either version 3 of the
#     License, or (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.

#     You should have received a copy of the GNU Affero General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""Feeds for Objectapp"""
from urlparse import urljoin
from BeautifulSoup import BeautifulSoup

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.utils.feedgenerator import Atom1Feed
from django.utils.translation import ugettext as _
from django.contrib.syndication.views import Feed
from django.core.urlresolvers import NoReverseMatch
from django.core.exceptions import ObjectDoesNotExist

from tagging.models import Tag
from tagging.models import TaggedItem

from objectapp.models import Gbobject
from objectapp.settings import COPYRIGHT
from objectapp.settings import PROTOCOL
from objectapp.settings import FEEDS_FORMAT
from objectapp.settings import FEEDS_MAX_ITEMS
from objectapp.managers import gbobjects_published
from objectapp.views.objecttypes import get_Objecttype_or_404
from objectapp.templatetags.objectapp_tags import get_gravatar


class ObjectappFeed(Feed):
    """Base Feed for Objectapp"""
    feed_copyright = COPYRIGHT

    def __init__(self):
        self.site = Site.objects.get_current()
        self.site_url = '%s://%s' % (PROTOCOL, self.site.domain)
        if FEEDS_FORMAT == 'atom':
            self.feed_type = Atom1Feed
            self.subtitle = self.description


class GbobjectFeed(ObjectappFeed):
    """Base Gbobject Feed"""
    title_template = 'feeds/gbobject_title.html'
    description_template = 'feeds/gbobject_description.html'

    def item_pubdate(self, item):
        """Publication date of an gbobject"""
        return item.creation_date

    def item_objecttypes(self, item):
        """Gbobject's objecttypes"""
        return [Objecttype.title for Objecttype in item.objecttypes.all()]

    def item_author_name(self, item):
        """Returns the first author of an gbobject"""
        if item.authors.count():
            self.item_author = item.authors.all()[0]
            return self.item_author.username

    def item_author_email(self, item):
        """Returns the first author's email"""
        return self.item_author.email

    def item_author_link(self, item):
        """Returns the author's URL"""
        try:
            author_url = reverse('objectapp_author_detail',
                                 args=[self.item_author.username])
            return self.site_url + author_url
        except NoReverseMatch:
            return self.site_url

    def item_enclosure_url(self, item):
        """Returns an image for enclosure"""
        if item.image:
            return item.image.url

        img = BeautifulSoup(item.html_content).find('img')
        if img:
            return urljoin(self.site_url, img['src'])

    def item_enclosure_length(self, item):
        """Hardcoded enclosure length"""
        return '100000'

    def item_enclosure_mime_type(self, item):
        """Hardcoded enclosure mimetype"""
        return 'image/jpeg'


class LatestGbobjects(GbobjectFeed):
    """Feed for the latest gbobjects"""

    def link(self):
        """URL of latest gbobjects"""
        return reverse('objectapp_gbobject_archive_index')

    def items(self):
        """Items are published gbobjects"""
        return Gbobject.published.all()[:FEEDS_MAX_ITEMS]

    def title(self):
        """Title of the feed"""
        return '%s - %s' % (self.site.name, _('Latest gbobjects'))

    def description(self):
        """Description of the feed"""
        return _('The latest gbobjects for the site %s') % self.site.name


class ObjecttypeGbobjects(GbobjectFeed):
    """Feed filtered by a Objecttype"""

    def get_object(self, request, path):
        """Retrieve the Objecttype by his path"""
        return get_Objecttype_or_404(path)

    def items(self, obj):
        """Items are the published gbobjects of the Objecttype"""
        return obj.gbobjects_published()[:FEEDS_MAX_ITEMS]

    def link(self, obj):
        """URL of the Objecttype"""
        return obj.get_absolute_url()

    def title(self, obj):
        """Title of the feed"""
        return _('Gbobjects for the Objecttype %s') % obj.title

    def description(self, obj):
        """Description of the feed"""
        return _('The latest gbobjects for the Objecttype %s') % obj.title


class AuthorGbobjects(GbobjectFeed):
    """Feed filtered by an author"""

    def get_object(self, request, username):
        """Retrieve the author by his username"""
        return get_object_or_404(User, username=username)

    def items(self, obj):
        """Items are the published gbobjects of the author"""
        return gbobjects_published(obj.gbobjects)[:FEEDS_MAX_ITEMS]

    def link(self, obj):
        """URL of the author"""
        return reverse('objectapp_author_detail', args=[obj.username])

    def title(self, obj):
        """Title of the feed"""
        return _('Gbobjects for author %s') % obj.username

    def description(self, obj):
        """Description of the feed"""
        return _('The latest gbobjects by %s') % obj.username


class TagGbobjects(GbobjectFeed):
    """Feed filtered by a tag"""

    def get_object(self, request, slug):
        """Retrieve the tag by his name"""
        return get_object_or_404(Tag, name=slug)

    def items(self, obj):
        """Items are the published gbobjects of the tag"""
        return TaggedItem.objects.get_by_model(
            Gbobject.published.all(), obj)[:FEEDS_MAX_ITEMS]

    def link(self, obj):
        """URL of the tag"""
        return reverse('objectapp_tag_detail', args=[obj.name])

    def title(self, obj):
        """Title of the feed"""
        return _('Gbobjects for the tag %s') % obj.name

    def description(self, obj):
        """Description of the feed"""
        return _('The latest gbobjects for the tag %s') % obj.name


class SearchGbobjects(GbobjectFeed):
    """Feed filtered by a search pattern"""

    def get_object(self, request):
        """The GET parameter 'pattern' is the object"""
        pattern = request.GET.get('pattern', '')
        if len(pattern) < 3:
            raise ObjectDoesNotExist
        return pattern

    def items(self, obj):
        """Items are the published gbobjects founds"""
        return Gbobject.published.search(obj)[:FEEDS_MAX_ITEMS]

    def link(self, obj):
        """URL of the search request"""
        return '%s?pattern=%s' % (reverse('objectapp_gbobject_search'), obj)

    def title(self, obj):
        """Title of the feed"""
        return _("Results of the search for '%s'") % obj

    def description(self, obj):
        """Description of the feed"""
        return _("The gbobjects containing the pattern '%s'") % obj


class GbobjectDiscussions(ObjectappFeed):
    """Feed for discussions in an gbobject"""
    title_template = 'feeds/discussion_title.html'
    description_template = 'feeds/discussion_description.html'

    def get_object(self, request, year, month, day, slug):
        """Retrieve the discussions by gbobject's slug"""
        return get_object_or_404(Gbobject.published, slug=slug,
                                 creation_date__year=year,
                                 creation_date__month=month,
                                 creation_date__day=day)

    def items(self, obj):
        """Items are the discussions on the gbobject"""
        return obj.discussions[:FEEDS_MAX_ITEMS]

    def item_pubdate(self, item):
        """Publication date of a discussion"""
        return item.submit_date

    def item_link(self, item):
        """URL of the discussion"""
        return item.get_absolute_url()

    def link(self, obj):
        """URL of the gbobject"""
        return obj.get_absolute_url()

    def item_author_name(self, item):
        """Author of the discussion"""
        return item.userinfo['name']

    def item_author_email(self, item):
        """Author's email of the discussion"""
        return item.userinfo['email']

    def item_author_link(self, item):
        """Author's URL of the discussion"""
        return item.userinfo['url']

    def title(self, obj):
        """Title of the feed"""
        return _('Discussions on %s') % obj.title

    def description(self, obj):
        """Description of the feed"""
        return _('The latest discussions for the gbobject %s') % obj.title


class GbobjectComments(GbobjectDiscussions):
    """Feed for comments in an gbobject"""
    title_template = 'feeds/comment_title.html'
    description_template = 'feeds/comment_description.html'

    def items(self, obj):
        """Items are the comments on the gbobject"""
        return obj.comments[:FEEDS_MAX_ITEMS]

    def item_link(self, item):
        """URL of the comment"""
        return item.get_absolute_url('#comment_%(id)s')

    def title(self, obj):
        """Title of the feed"""
        return _('Comments on %s') % obj.title

    def description(self, obj):
        """Description of the feed"""
        return _('The latest comments for the gbobject %s') % obj.title

    def item_enclosure_url(self, item):
        """Returns a gravatar image for enclosure"""
        return get_gravatar(item.userinfo['email'])

    def item_enclosure_length(self, item):
        """Hardcoded enclosure length"""
        return '100000'

    def item_enclosure_mime_type(self, item):
        """Hardcoded enclosure mimetype"""
        return 'image/jpeg'


class GbobjectPingbacks(GbobjectDiscussions):
    """Feed for pingbacks in an gbobject"""
    title_template = 'feeds/pingback_title.html'
    description_template = 'feeds/pingback_description.html'

    def items(self, obj):
        """Items are the pingbacks on the gbobject"""
        return obj.pingbacks[:FEEDS_MAX_ITEMS]

    def item_link(self, item):
        """URL of the pingback"""
        return item.get_absolute_url('#pingback_%(id)s')

    def title(self, obj):
        """Title of the feed"""
        return _('Pingbacks on %s') % obj.title

    def description(self, obj):
        """Description of the feed"""
        return _('The latest pingbacks for the gbobject %s') % obj.title


class GbobjectTrackbacks(GbobjectDiscussions):
    """Feed for trackbacks in an gbobject"""
    title_template = 'feeds/trackback_title.html'
    description_template = 'feeds/trackback_description.html'

    def items(self, obj):
        """Items are the trackbacks on the gbobject"""
        return obj.trackbacks[:FEEDS_MAX_ITEMS]

    def item_link(self, item):
        """URL of the trackback"""
        return item.get_absolute_url('#trackback_%(id)s')

    def title(self, obj):
        """Title of the feed"""
        return _('Trackbacks on %s') % obj.title

    def description(self, obj):
        """Description of the feed"""
        return _('The latest trackbacks for the gbobject %s') % obj.title
