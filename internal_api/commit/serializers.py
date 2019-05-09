import asyncio
import logging

from rest_framework import serializers

from archive.services import ReportService
from repo_providers.services import RepoProviderService
from internal_api.repo.models import Repository
from codecov_auth.models import Owner
from .models import Commit

log = logging.getLogger(__name__)


class CommitAuthorSerializer(serializers.ModelSerializer):
    username = serializers.CharField()
    email = serializers.CharField()
    name = serializers.CharField()

    class Meta:
        model = Owner
        fields = ('username', 'email', 'name')


class CommitRepoSerializer(serializers.ModelSerializer):
    repoid = serializers.IntegerField()
    name = serializers.CharField()
    updatestamp = serializers.DateTimeField()

    class Meta:
        model = Repository
        fields = ('repoid', 'name', 'updatestamp')


class ShortParentlessCommitSerializer(serializers.ModelSerializer):
    commitid = serializers.CharField()
    message = serializers.CharField()
    timestamp = serializers.DateTimeField()
    ci_passed = serializers.BooleanField()
    author = CommitAuthorSerializer()
    repository = CommitRepoSerializer()
    branch = serializers.CharField()
    totals = serializers.JSONField()

    class Meta:
        model = Commit
        fields = ('commitid', 'message', 'timestamp', 'ci_passed',
                  'author', 'repository', 'branch', 'totals')


class ParentlessCommitSerializer(ShortParentlessCommitSerializer):
    report = serializers.SerializerMethodField()
    # src = serializers.SerializerMethodField()

    def get_report(self, obj):
        log.info("========================================")
        log.info("GET_REPORT")
        log.info("========================================")
        report = ReportService().build_report_from_commit(obj)
        return ReportSerializer(instance=report).data

    # def get_src(self, obj):
    #     loop = asyncio.get_event_loop()
    #     user = self.context.get("user")
    #     task = RepoProviderService().get_adapter(
    #         user, obj.repository).get_commit_diff(obj.commitid)
    #     return loop.run_until_complete(task)

    class Meta:
        model = Commit
        fields = ('report', 'commitid', 'timestamp', 'updatestamp',
                  'ci_passed', 'repository', 'author', 'message')


class CommitSerializer(ParentlessCommitSerializer):
    parent = ParentlessCommitSerializer(source='parent_commit')

    class Meta:
        model = Commit
        fields = ('src', 'commitid', 'timestamp', 'updatestamp',
                  'ci_passed', 'report', 'repository', 'parent', 'author')


class ReportFileSerializer(serializers.Serializer):
    name = serializers.CharField()
    lines = serializers.SerializerMethodField()
    totals = serializers.JSONField(source='totals._asdict')

    def get_lines(self, obj):
        return list(self.get_lines_iterator(obj))

    def get_lines_iterator(self, obj):
        for line_number, line in obj.lines:
            coverage, line_type, sessions, messages, complexity = line
            sessions = [list(s) for s in sessions]
            yield (line_number, coverage, line_type, sessions, messages, complexity)


class ReportSerializer(serializers.Serializer):
    totals = serializers.JSONField(source='totals._asdict')
    files = ReportFileSerializer(source='file_reports', many=True)
