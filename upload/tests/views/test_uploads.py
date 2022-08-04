from unittest.mock import patch
from uuid import uuid4

import pytest
from django.forms import ValidationError
from django.urls import reverse
from rest_framework.test import APIClient

from core.tests.factories import CommitFactory, RepositoryFactory
from reports.models import CommitReport
from upload.views.uploads import UploadViews


def test_uploads_get_not_allowed(client):
    url = reverse("new_upload.uploads", args=["the-repo", "commit-sha", "report-id"])
    assert url == "/upload/the-repo/commits/commit-sha/reports/report-id/uploads"
    res = client.get(url)
    assert res.status_code == 405


def test_get_repo(db):
    repository = RepositoryFactory(name="the_repo", author__username="codecov")
    repository.save()
    upload_views = UploadViews()
    upload_views.kwargs = dict(repo=repository.name)
    recovered_repo = upload_views.get_repo()
    assert recovered_repo == repository


@patch("shared.metrics.metrics.incr")
def test_get_repo_error(mock_metrics, db):
    upload_views = UploadViews()
    upload_views.kwargs = dict(repo="repo_missing")
    with pytest.raises(ValidationError):
        upload_views.get_repo()
    mock_metrics.assert_called_once_with("uploads.rejected", 1)


def test_get_commit(db):
    repository = RepositoryFactory(name="the_repo", author__username="codecov")
    commit = CommitFactory(repository=repository)
    repository.save()
    commit.save()
    upload_views = UploadViews()
    upload_views.kwargs = dict(repo=repository.name, commit_sha=commit.commitid)
    recovered_commit = upload_views.get_commit()
    assert recovered_commit == commit


@patch("shared.metrics.metrics.incr")
def test_get_commit_error(mock_metrics, db):
    repository = RepositoryFactory(name="the_repo", author__username="codecov")
    repository.save()
    upload_views = UploadViews()
    upload_views.kwargs = dict(repo=repository.name, commit_sha="missing_commit")
    with pytest.raises(ValidationError):
        upload_views.get_commit()
    mock_metrics.assert_called_once_with("uploads.rejected", 1)


def test_get_report(db):
    repository = RepositoryFactory(name="the_repo", author__username="codecov")
    commit = CommitFactory(repository=repository)
    report = CommitReport(commit=commit)
    repository.save()
    commit.save()
    report.save()
    upload_views = UploadViews()
    upload_views.kwargs = dict(
        repo=repository.name, commit_sha=commit.commitid, reportid=report.external_id
    )
    recovered_report = upload_views.get_report()
    assert recovered_report == report


@patch("shared.metrics.metrics.incr")
def test_get_report_error(mock_metrics, db):
    repository = RepositoryFactory(name="the_repo", author__username="codecov")
    commit = CommitFactory(repository=repository)
    wrong_reportid = str(uuid4())
    repository.save()
    commit.save()
    upload_views = UploadViews()
    upload_views.kwargs = dict(
        repo=repository.name, commit_sha=commit.commitid, reportid=wrong_reportid
    )
    with pytest.raises(ValidationError):
        upload_views.get_report()
        mock_metrics.assert_called_once_with("uploads.rejected", 1)


@patch("shared.metrics.metrics.incr")
def test_uploads_post_empty(mock_metrics, db, mocker, mock_redis):
    presigned_put_mock = mocker.patch(
        "services.archive.StorageService.create_presigned_put",
        return_value="presigned put",
    )
    repository = RepositoryFactory(name="the_repo", author__username="codecov")
    commit = CommitFactory(repository=repository)
    commit_report = CommitReport.objects.create(commit=commit)
    repository.save()
    commit_report.save()

    owner = repository.author
    client = APIClient()
    client.force_authenticate(user=owner)
    url = reverse(
        "new_upload.uploads",
        args=[repository.name, commit.commitid, commit_report.external_id],
    )
    response = client.post(
        url,
        {"state": "uploaded"},
        format="json",
    )
    response_json = response.json()
    assert response.status_code == 201
    assert all(
        map(
            lambda x: x in response_json.keys(),
            ["external_id", "created_at", "raw_upload_location"],
        )
    )
    mock_metrics.assert_called_once_with("uploads.accepted", 1)
    presigned_put_mock.assert_called()
