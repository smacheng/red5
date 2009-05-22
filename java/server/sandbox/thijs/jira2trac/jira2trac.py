#!/usr/bin/env python3.1
# Copyright Thijs Triemstra 2008-2009

"""
Import a Jira backup into a Trac database using XML-RPC.

@since: 2008-12-20
@author: Thijs Triemstra
"""

import io, os, stat, time
import xml.parsers.expat

from decimal import Decimal
from xmlrpc import client
from datetime import datetime

class JiraDecoder(object):
    """
    Load Jira backup file
    """
    def __init__(self, input, logger):
        if input:
            self.log = logger
            self.input = input
            self.lastItem = None
            self.allItems = []
            self.data = dict()
            self.data['versions'] = []
            self.data['resolutions'] = []
            self.data['projects'] = []
            self.data['priorities'] = []
            self.data['users'] = []
            self.data['issues'] = []
            self.data['components'] = []
            self.data['customFieldValues'] = []
            self.data['eventTypes'] = []
            self.data['attachments'] = []
            self.data['issueTypes'] = []
            self.data['groups'] = []
            self.data['memberships'] = []
            self.data['statuses'] = []
            self.data['actions'] = []
            self.size = Decimal(str(os.stat(input)[stat.ST_SIZE]/(1024*1024))
                                ).quantize(Decimal('.01'))

            logger.info('%s...' % self.__doc__.strip())
            logger.info('Reading data from %s (%s MB)' % (input, self.size))
            logger.info('Processing data...')
        else:
            raise BaseException("Please specify the 'input' option")
            
    def parseBackupFile(self):
        """
        Load the Jira XML backup dump file and start parsing it.
        """
        markup = io.FileIO(self.input, 'r').readall()
        
        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = self._start_element
        p.EndElementHandler = self._end_element
        p.CharacterDataHandler = self._char_data
        p.Parse(markup, 1)
    
    def showResults(self):
        """
        Print the parse results on stdout.
        """       
        categories = ['versions', 'resolutions', 'projects', 'priorities',
                      'components', 'issueTypes', 'groups', 'issues',
                      'attachments', 'users', 'actions']
        
        for category in categories:
            name = category.title()
            
            if category == 'issueTypes':
                name = 'Issue Types'
            
            self.log.info('  %d %s' % (len(self.data[category]), name))
        
        for item in self.data['users']:
            print('%50s - %s' % (item['name'], item['password']))
                    
    def _addItem(self, category, data):
        self.data[category].append(data)
        self.allItems.append(data)
        self.category = category
    
    def _char_data(self, data):
        self.log.debug('Character data: %s' % repr(data))
            
        if self.lastItem:
            try:
                # start update
                self._updateItem(data)
            except KeyError:
                pass
    
    def _updateItem(self, data):
        if (data != "'\n'") or (data[1:len(data)-1].isspace() == False):
            self.lastItem['body'] += data
        
    def _end_element(self, name):
        self.log.debug('End element: %s' % name)
    
        if name == 'body':
            # finish update
            self.data[self.category][len(self.data[self.category])-1] = self.lastItem
            self.lastItem = None

    def _start_element(self, name, attrs):
        self.log.debug('Start element: %s %s' % (name, attrs))
            
        if name == 'Version':
            version = {'number':attrs['name']}
            try:
                version['description'] = attrs['description']
            except KeyError:
                version['description'] = None
            
            try:
                version['releasedate'] = datetime.strptime(attrs['releasedate'][:-2],
                                                           '%Y-%m-%d %H:%M:%S')
            except KeyError:
                version['releasedate'] = 0
                
            self._addItem('versions', version)
            
        elif name == 'Resolution':
            resolution = {'name': attrs['name'], 'description': attrs['description']}
            
            self._addItem('resolutions', resolution)
        
        elif name == 'Status':
            status = {'id': attrs['id'], 'sequence': attrs['sequence'],
                      'name': attrs['name'], 'description': attrs['description']}
            
            self._addItem('statuses', status)
            
        elif name == 'Project':
            project = {'name': attrs['name'], 'owner': attrs['lead'],
                       'description': attrs['description'], 'id': attrs['id']}
            
            self._addItem('projects', project)
        
        elif name == 'Priority':
            priority = {'name': attrs['name'], 'description': attrs['description'],
                        'id': attrs['id']}
            
            self._addItem('priorities', priority)
        
        elif name == 'OSUser':
            user = {'name': attrs['name'], 'id': attrs['id']}
            
            try:
                user['password'] = attrs['passwordHash']
                self._addItem('users', user)
            except KeyError:
                pass
    
        elif name == 'Issue':
            issue = {'project': attrs['project'], 'id': attrs['id'],
                     'reporter': attrs['reporter'], 'assignee': attrs['assignee'],
                     'type': attrs['type'], 'summary': attrs['summary'],
                     'priority': attrs['priority'], 'status': attrs['status'],
                     'created': attrs['created'], 'votes': attrs['votes']}
            
            try:
                issue['resolution'] = attrs['resolution']
            except KeyError:
                pass
                
            self._addItem('issues', issue)
        
        elif name == 'Component':
            component = {'project': attrs['project'], 'id': attrs['id'],
                         'name': attrs['name'], 'description': attrs['description'],
                         'owner': attrs['lead']}

            self._addItem('components', component)
        
        elif name == 'CustomFieldValue' and attrs['customfield'] == '10001':
            customFieldValue = {'issue': attrs['issue'], 'id': attrs['id'],
                                'value': attrs['stringvalue']}

            self._addItem('customFieldValues', customFieldValue)
         
        elif name == 'EventType':
            eventType = {'id': attrs['id'], 'name': attrs['name'],
                         'description': attrs['description']}

            self._addItem('eventTypes', eventType)
        
        elif name == 'IssueType':
            issueType = {'id': attrs['id'], 'sequence': attrs['sequence'],
                         'name': attrs['name'], 'description': attrs['description']}

            self._addItem('issueTypes', issueType)
            
        elif name == 'FileAttachment':
            attachment = {'id': attrs['id'], 'issue': attrs['issue'],
                         'mimetype': attrs['mimetype'], 'created': attrs['created'],
                         'filename': attrs['filename'], 'filesize': attrs['filesize'],
                         'author': attrs['author']}

            self._addItem('attachments', attachment)
        
        elif name == 'OSGroup':
            group = {'id': attrs['id'], 'name': attrs['name']}

            self._addItem('groups', group)
        
        elif name == 'Action':
            action = {'id': attrs['id'], 'issue': attrs['issue'],
                      'author': attrs['author'], 'type': attrs['type'],
                      'created': attrs['created']}

            try:
                action['body'] = attrs['body']
            except KeyError:
                pass
            
            self._addItem('actions', action)
            
        elif name == 'OSMembership':
            membership = {'id': attrs['id'], 'username': attrs['userName'],
                          'groupName': attrs['groupName']}

            self._addItem('memberships', membership)
        
        elif name == 'body':
            # create update object
            self.lastItem = self.allItems[len(self.allItems)-1]
            self.lastItem['body'] = ''
        
        # Unused:
        #  - OSCurrentStep
        #  - OSCurrentStepPrev
        #  - OSHistoryStep
        #  - OSHistoryStepPrev
        #  - OSPropertyEntry
        #  - OSPropertyString
        #  - OSWorkflowEntry
        #  - UserAssociation

class TracEncoder(object):
    """
    Save data in remote Trac database using XML-RPC
    """
    def __init__(self, username, password, url, logger):
        if url:
            self.url = url
            self.username = username
            self.password = password
            self.log = logger
            
            if username is not None and password is not None:
                auth = '%s:%s@' % (username, password)
            else:
                auth = ''
            
            self.location = "http://%s%s/login/xmlrpc" % (auth, url)
            self.log.info('%s...' % self.__doc__.strip())
            
        else:
            raise BaseException("Please specify a value for the 'url' option")
    
    def importData(self, jiraData):
        """
        Save all data to the Trac database.
        """
        self.log.info('Connecting to %s' % self.location)
        
        self.jiraData = jiraData
        self.proxy = client.ServerProxy(self.location, use_datetime=True)

        self.log.info('Importing data...')
        self.call(self.importVersions)
        self.call(self.importResolutions)
        self.call(self.importPriorities)
        self.call(self.importIssueTypes)
        self.call(self.importMilestones)
        self.call(self.importComponents)
        self.call(self.importUsers)
        self.call(self.importIssues)
        self.call(self.importActions)
        self.call(self.importAttachments)

    def call(self, func):
        """
        Invoke a method and handle exceptions.
        """
        try:
            func()

        except client.ProtocolError as err:
            self.log.error("A protocol error occurred!")
            self.log.error("URL: %s" % err.url)
            self.log.error("HTTP/HTTPS headers: %s" % err.headers)
            self.log.error("Error: %d - %s" % (err.errcode, err.errmsg))

        except client.Fault as err:
            self.log.error("A fault occurred!")
            self.log.error("Fault code: %d" % err.faultCode)
            self.log.error("Fault string: %s" % err.faultString)

    def importVersions(self):
        # get existing versions from trac
        versions = self.proxy.ticket.version.getAll()
         
        # remove existing versions from trac if necessary
        if len(versions) > 0:
            for version in versions:
                self.proxy.ticket.version.delete(version)
    
        # import new versions into trac
        for version in self.jiraData['versions']:
            # exclude trailing 'v' from version number
            nr = version['number'][1:]
            desc = version['description']
            date = version['releasedate']
            attr = {'name': nr, 'time': date, 'description': desc}
            self.proxy.ticket.version.create(nr, attr)
        
        self.log.info('  %d Versions' % len(self.jiraData['versions']))
        
    def importResolutions(self):
        # get existing resolutions from trac
        resolutions = self.proxy.ticket.resolution.getAll()
         
        # remove existing resolutions from trac if necessary
        if len(resolutions) > 0:
            for resolution in resolutions:
                self.proxy.ticket.resolution.delete(resolution)
    
        # import new resolutions into trac
        order = 1
        for resolution in self.jiraData['resolutions']:
            name = resolution['name']
            self.proxy.ticket.resolution.create(name, order)
            order += 1
        
        self.log.info('  %d Resolutions' % len(self.jiraData['resolutions']))
    
    def importPriorities(self):
        # get existing priorities from trac
        priorities = self.proxy.ticket.priority.getAll()
         
        # remove existing priorities from trac if necessary
        if len(priorities) > 0:
            for priority in priorities:
                self.proxy.ticket.priority.delete(priority)
    
        # import new priorities into trac
        order = 1
        for priority in self.jiraData['priorities']:
            name = priority['name']
            self.proxy.ticket.priority.create(name, order)
            order += 1
        
        self.log.info('  %d Priorities' % len(self.jiraData['priorities']))

    def importIssueTypes(self):
        # get existing issue types from trac
        issueTypes = self.proxy.ticket.type.getAll()
         
        # remove existing issue types from trac if necessary
        if len(issueTypes) > 0:
            for issueType in issueTypes:
                self.proxy.ticket.type.delete(issueType)
    
        # import new issue types into trac
        for issueType in self.jiraData['issueTypes']:
            name = issueType['name']
            order = issueType['sequence']
            self.proxy.ticket.type.create(name, order)
        
        self.log.info('  %d Issue Types' % len(self.jiraData['issueTypes']))
    
    def importMilestones(self):
        # get existing milestones from trac
        milestones = self.proxy.ticket.milestone.getAll()
         
        # seems Jira doesn't support milestones or we never used them
        # so remove all existing milestones from trac
        if len(milestones) > 0:
            for milestone in milestones:
                self.proxy.ticket.milestone.delete(milestone)
    
    def importComponents(self):
        # get existing components from trac
        components = self.proxy.ticket.component.getAll()

        # remove existing components from trac if necessary
        if len(components) > 0:
            for component in components:
                self.proxy.ticket.component.delete(component)
        
        # import new components into trac
        # note: we import jira's projects as components in trac
        for component in self.jiraData['projects']:
            name = component['name']
            owner = component['owner']
            desc = component['description']
            attr = {'name': name, 'owner': owner, 'description': desc}
            self.proxy.ticket.component.create(name, attr)
        
        self.log.info('  %d Components' % len(self.jiraData['projects']))
                                              
    def importUsers(self):
        pass
    
    def importIssues(self):
        pass
    
    def importActions(self):
        pass
    
    def importAttachments(self):
        pass
            
if __name__ == "__main__":
    import logging
    from optparse import OptionParser
    
    usage = "Usage: Jira2Trac [options]"
    parser = OptionParser(usage=usage, version="Jira2Trac 1.0")
    
    parser.add_option("-i", "--input", dest="input", 
                      help="Load Jira backup data from XML file", metavar="FILE")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="Print debug messages to stdout [default: %default]")
    parser.add_option("-u", "--username", dest="username", help="Username for Trac instance")
    parser.add_option("-p", "--password", dest="password", help="Password for Trac instance")
    parser.add_option("-l", "--url", dest="url", help="URL for Trac instance")
    (options, args) = parser.parse_args()
    
    # create logger
    FORMAT = "%(asctime)-15s - %(message)s"
    LEVEL = logging.INFO

    if options.verbose == True:
        LEVEL = logging.DEBUG
    
    logging.basicConfig(format=FORMAT, level=LEVEL)

    if options.input:
        start = time.time()
        
        jira = JiraDecoder(options.input, logging)
        jira.parseBackupFile()
        jira.showResults()
        
        if options.username:
            trac = TracEncoder(options.username, options.password, options.url, logging)
            trac.importData(jira.data)
        
        end = time.time() - start

        logging.info('Completed in %s sec.\n' % (Decimal(str(end)).quantize(Decimal('.0001'))))
        
    else:
        parser.error("Please specify a value for the 'input' option")