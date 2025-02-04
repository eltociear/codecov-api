from datetime import datetime
from unittest.mock import patch

import pytest
from ddf import G
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITransactionTestCase

from codecov_auth.tests.factories import OwnerFactory
from core.models import Pull
from core.tests.factories import PullFactory, RepositoryFactory
from utils.test_utils import APIClient


class UserViewSetTests(APITransactionTestCase):
    def setUp(self):
        non_org_active_user = OwnerFactory()
        self.current_owner = OwnerFactory(
            plan="users-free",
            plan_user_count=5,
            plan_activated_users=[non_org_active_user.ownerid],
        )
        self.users = [
            non_org_active_user,
            OwnerFactory(organizations=[self.current_owner.ownerid]),
            OwnerFactory(organizations=[self.current_owner.ownerid]),
            OwnerFactory(organizations=[self.current_owner.ownerid]),
        ]

        self.client = APIClient()
        self.client.force_login_owner(self.current_owner)

    def _list(self, kwargs={}, query_params={}):
        if not kwargs:
            kwargs = {
                "service": self.current_owner.service,
                "owner_username": self.current_owner.username,
            }
        return self.client.get(reverse("users-list", kwargs=kwargs), data=query_params)

    def _patch(self, kwargs, data):
        return self.client.patch(reverse("users-detail", kwargs=kwargs), data=data)

    def test_list_returns_200_and_user_list_on_success(self):
        response = self._list()
        assert response.status_code == status.HTTP_200_OK
        expected = [
            {
                "name": user.name,
                "is_admin": False,
                "activated": user.ownerid in self.current_owner.plan_activated_users,
                "username": user.username,
                "email": user.email,
                "ownerid": user.ownerid,
                "student": user.student,
                "last_pull_timestamp": None,
            }
            for user in self.users
        ]
        self.assertCountEqual(response.data["results"], expected)

    def test_list_sets_activated(self):
        self.current_owner.plan_activated_users = [self.users[0].ownerid]
        self.current_owner.save()

        response = self._list()

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"][0] == {
            "name": self.users[0].name,
            "activated": True,
            "is_admin": False,
            "username": self.users[0].username,
            "email": self.users[0].email,
            "ownerid": self.users[0].ownerid,
            "student": self.users[0].student,
            "last_pull_timestamp": None,
        }

    def test_list_sets_is_admin(self):
        self.current_owner.admins = [self.users[1].ownerid]
        self.current_owner.save()

        response = self._list()

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"][1] == {
            "name": self.users[1].name,
            "activated": False,
            "is_admin": True,
            "username": self.users[1].username,
            "email": self.users[1].email,
            "ownerid": self.users[1].ownerid,
            "student": self.users[1].student,
            "last_pull_timestamp": None,
        }

    def test_list_can_filter_by_activated(self):
        self.current_owner.plan_activated_users = [self.users[0].ownerid]
        self.current_owner.save()

        response = self._list(query_params={"activated": True})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == [
            {
                "name": self.users[0].name,
                "activated": True,
                "is_admin": False,
                "username": self.users[0].username,
                "email": self.users[0].email,
                "ownerid": self.users[0].ownerid,
                "student": self.users[0].student,
                "last_pull_timestamp": None,
            }
        ]

    def test_list_can_filter_by_is_admin(self):
        self.current_owner.admins = [self.users[1].ownerid]
        self.current_owner.save()

        response = self._list(query_params={"is_admin": True})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == [
            {
                "name": self.users[1].name,
                "activated": False,
                "is_admin": True,
                "username": self.users[1].username,
                "email": self.users[1].email,
                "ownerid": self.users[1].ownerid,
                "student": self.users[1].student,
                "last_pull_timestamp": None,
            }
        ]

    def test_list_can_search_by_username(self):
        # set up some names
        self.users[0].username = "thanos"
        self.users[0].save()
        self.users[1].username = "thor23"
        self.users[1].save()
        self.users[2].username = "thor"
        self.users[2].save()

        response = self._list(query_params={"search": "hor"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == [
            {
                "name": self.users[1].name,
                "activated": False,
                "is_admin": False,
                "username": "thor23",
                "email": self.users[1].email,
                "ownerid": self.users[1].ownerid,
                "student": self.users[1].student,
                "last_pull_timestamp": None,
            },
            {
                "name": self.users[2].name,
                "activated": False,
                "is_admin": False,
                "username": "thor",
                "email": self.users[2].email,
                "ownerid": self.users[2].ownerid,
                "student": self.users[2].student,
                "last_pull_timestamp": None,
            },
        ]

    @pytest.mark.skip
    def test_list_can_search_by_name(self):
        # set up some names
        self.users[0].name = "thanos"
        self.users[0].save()
        self.users[1].name = "thor23"
        self.users[1].save()
        self.users[2].name = "thor"
        self.users[2].save()

        response = self._list(query_params={"search": "tho"})
        assert response.status_code == status.HTTP_200_OK
        expected_result = [
            {
                "name": "thor23",
                "activated": False,
                "is_admin": False,
                "username": self.users[1].username,
                "email": self.users[1].email,
                "ownerid": self.users[1].ownerid,
                "student": self.users[1].student,
                "last_pull_timestamp": None,
            },
            {
                "name": "thor",
                "activated": False,
                "is_admin": False,
                "username": self.users[2].username,
                "email": self.users[2].email,
                "ownerid": self.users[2].ownerid,
                "student": self.users[2].student,
                "last_pull_timestamp": None,
            },
        ]
        assert response.data["results"][0] == expected_result[0]
        assert response.data["results"][1] == expected_result[1]
        assert response.data["results"] == expected_result

    @pytest.mark.skip(reason="flaky, skipping until re write")
    def test_list_can_search_by_email(self):
        # set up some names
        self.users[0].email = "thanos@gmail.com"
        self.users[0].save()
        self.users[1].email = "ironman@gmail.com"
        self.users[1].save()
        self.users[2].email = "thor@gmail.com"
        self.users[2].save()

        response = self._list(query_params={"search": "th"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == [
            {
                "name": self.users[0].name,
                "activated": False,
                "is_admin": False,
                "username": self.users[0].username,
                "email": "thanos@gmail.com",
                "ownerid": self.users[0].ownerid,
                "student": self.users[0].student,
                "last_pull_timestamp": None,
            },
            {
                "name": self.users[2].name,
                "activated": False,
                "is_admin": False,
                "username": self.users[2].username,
                "email": "thor@gmail.com",
                "ownerid": self.users[2].ownerid,
                "student": self.users[2].student,
                "last_pull_timestamp": None,
            },
        ]

    def test_list_can_order_by_name(self):
        self.users[0].name = "a"
        self.users[0].save()
        self.users[1].name = "b"
        self.users[1].save()
        self.users[2].name = "c"
        self.users[2].save()
        self.users[3].name = "d"
        self.users[3].save()

        response = self._list(query_params={"ordering": "name"})

        assert [r["name"] for r in response.data["results"]] == ["a", "b", "c", "d"]

        response = self._list(query_params={"ordering": "-name"})

        assert [r["name"] for r in response.data["results"]] == ["d", "c", "b", "a"]

    def test_list_can_order_by_username(self):
        self.users[0].username = "a"
        self.users[0].save()
        self.users[1].username = "b"
        self.users[1].save()
        self.users[2].username = "c"
        self.users[2].save()
        self.users[3].username = "d"
        self.users[3].save()

        response = self._list(query_params={"ordering": "username"})

        assert [r["username"] for r in response.data["results"]] == ["a", "b", "c", "d"]

        response = self._list(query_params={"ordering": "-username"})

        assert [r["username"] for r in response.data["results"]] == ["d", "c", "b", "a"]

    def test_list_can_order_by_email(self):
        self.users[0].email = "a"
        self.users[0].save()
        self.users[1].email = "b"
        self.users[1].save()
        self.users[2].email = "c"
        self.users[2].save()
        self.users[3].email = "d"
        self.users[3].save()

        response = self._list(query_params={"ordering": "email"})

        assert [r["email"] for r in response.data["results"]] == ["a", "b", "c", "d"]

        response = self._list(query_params={"ordering": "-email"})

        assert [r["email"] for r in response.data["results"]] == ["d", "c", "b", "a"]

    def test_list_can_order_by_activated(self):
        self.users[0].activated = False
        self.users[0].save()
        self.users[1].activated = True
        self.users[1].save()
        self.users[2].activated = False
        self.users[2].save()
        self.users[3].activated = False
        self.users[3].save()

        response = self._list(query_params={"ordering": "activated"})

        assert [r["activated"] for r in response.data["results"]] == [
            False,
            False,
            False,
            True,
        ]

        response = self._list(query_params={"ordering": "-activated"})

        assert [r["activated"] for r in response.data["results"]] == [
            True,
            False,
            False,
            False,
        ]

    @patch("api.internal.owner.views.on_enterprise_plan")
    def test_list_can_order_by_last_pull_timestamp(self, on_enterprise_plan):
        on_enterprise_plan.return_value = True

        repo = RepositoryFactory()
        pull1 = PullFactory(author=self.users[1], repository=repo)
        pull2 = PullFactory(author=self.users[2], repository=repo)

        # avoid `save` which sets `updatestamp`
        Pull.objects.filter(pk=pull1.pk).update(
            updatestamp=datetime(2022, 1, 1, 0, 0, 0)
        )
        Pull.objects.filter(pk=pull2.pk).update(
            updatestamp=datetime(2022, 2, 1, 0, 0, 0)
        )

        response = self._list(query_params={"ordering": "last_pull_timestamp"})
        assert [r["ownerid"] for r in response.data["results"]] == [
            self.users[0].ownerid,
            self.users[3].ownerid,
            self.users[1].ownerid,
            self.users[2].ownerid,
        ]
        assert [r["last_pull_timestamp"] for r in response.data["results"]] == [
            None,
            None,
            datetime(2022, 1, 1, 0, 0, 0),
            datetime(2022, 2, 1, 0, 0, 0),
        ]

        response = self._list(query_params={"ordering": "-last_pull_timestamp"})
        assert [r["ownerid"] for r in response.data["results"]] == [
            self.users[2].ownerid,
            self.users[1].ownerid,
            self.users[0].ownerid,
            self.users[3].ownerid,
        ]
        assert [r["last_pull_timestamp"] for r in response.data["results"]] == [
            datetime(2022, 2, 1, 0, 0, 0),
            datetime(2022, 1, 1, 0, 0, 0),
            None,
            None,
        ]

    def test_patch_with_ownerid(self):
        response = self._patch(
            kwargs={
                "service": self.current_owner.service,
                "owner_username": self.current_owner.username,
                "user_username_or_ownerid": self.users[0].ownerid,
            },
            data={"activated": True},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "name": self.users[0].name,
            "activated": True,
            "is_admin": False,
            "username": self.users[0].username,
            "email": self.users[0].email,
            "ownerid": self.users[0].ownerid,
            "student": self.users[0].student,
            "last_pull_timestamp": None,
        }

    def test_patch_can_set_activated_to_true(self):
        response = self._patch(
            kwargs={
                "service": self.current_owner.service,
                "owner_username": self.current_owner.username,
                "user_username_or_ownerid": self.users[0].username,
            },
            data={"activated": True},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "name": self.users[0].name,
            "activated": True,
            "is_admin": False,
            "username": self.users[0].username,
            "email": self.users[0].email,
            "ownerid": self.users[0].ownerid,
            "student": self.users[0].student,
            "last_pull_timestamp": None,
        }

        self.current_owner.refresh_from_db()
        assert self.users[0].ownerid in self.current_owner.plan_activated_users

    def test_patch_can_set_activated_to_false(self):
        # setup activated user
        self.current_owner.plan_activated_users = [self.users[1].ownerid]
        self.current_owner.save()

        response = self._patch(
            kwargs={
                "service": self.current_owner.service,
                "owner_username": self.current_owner.username,
                "user_username_or_ownerid": self.users[1].username,
            },
            data={"activated": False},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "name": self.users[1].name,
            "activated": False,
            "is_admin": False,
            "username": self.users[1].username,
            "email": self.users[1].email,
            "ownerid": self.users[1].ownerid,
            "student": self.users[1].student,
            "last_pull_timestamp": None,
        }

        self.current_owner.refresh_from_db()
        assert self.users[1].ownerid not in self.current_owner.plan_activated_users

    @patch("services.segment.SegmentService.account_deactivated_user")
    @patch("services.segment.SegmentService.account_activated_user")
    def test_user_activation_or_deactivation_triggers_segment_events(
        self, activated_event_mock, deactivated_event_mock
    ):
        response = self._patch(
            kwargs={
                "service": self.current_owner.service,
                "owner_username": self.current_owner.username,
                "user_username_or_ownerid": self.users[0].username,
            },
            data={"activated": True},
        )

        activated_event_mock.assert_called_once_with(
            current_user_ownerid=self.current_owner.ownerid,
            ownerid_to_activate=self.users[0].ownerid,
            org_ownerid=self.current_owner.ownerid,
        )

        response = self._patch(
            kwargs={
                "service": self.current_owner.service,
                "owner_username": self.current_owner.username,
                "user_username_or_ownerid": self.users[0].username,
            },
            data={"activated": False},
        )

        deactivated_event_mock.assert_called_once_with(
            current_user_ownerid=self.current_owner.ownerid,
            ownerid_to_deactivate=self.users[0].ownerid,
            org_ownerid=self.current_owner.ownerid,
        )

    @patch("codecov_auth.models.Owner.can_activate_user", lambda self, user: False)
    def test_patch_returns_403_if_cannot_activate_user(self):
        response = self._patch(
            kwargs={
                "service": self.current_owner.service,
                "owner_username": self.current_owner.username,
                "user_username_or_ownerid": self.users[0].username,
            },
            data={"activated": True},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_patch_can_set_is_admin_to_true(self):
        response = self._patch(
            kwargs={
                "service": self.current_owner.service,
                "owner_username": self.current_owner.username,
                "user_username_or_ownerid": self.users[2].username,
            },
            data={"is_admin": True},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "name": self.users[2].name,
            "activated": False,
            "is_admin": True,
            "username": self.users[2].username,
            "email": self.users[2].email,
            "ownerid": self.users[2].ownerid,
            "student": self.users[2].student,
            "last_pull_timestamp": None,
        }

        self.current_owner.refresh_from_db()
        assert self.users[2].ownerid in self.current_owner.admins

    def test_patch_can_set_is_admin_to_false(self):
        self.current_owner.admins = [self.users[2].ownerid]
        self.current_owner.save()

        response = self._patch(
            kwargs={
                "service": self.current_owner.service,
                "owner_username": self.current_owner.username,
                "user_username_or_ownerid": self.users[2].username,
            },
            data={"is_admin": False},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "name": self.users[2].name,
            "activated": False,
            "is_admin": False,
            "username": self.users[2].username,
            "email": self.users[2].email,
            "ownerid": self.users[2].ownerid,
            "student": self.users[2].student,
            "last_pull_timestamp": None,
        }

        self.current_owner.refresh_from_db()
        assert self.users[2].ownerid not in self.current_owner.admins
