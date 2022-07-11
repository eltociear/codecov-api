from ariadne import ObjectType
from asgiref.sync import sync_to_async

from graphql_api.dataloader.commit import CommitLoader
from graphql_api.dataloader.comparison import ComparisonLoader
from graphql_api.dataloader.owner import OwnerLoader
from graphql_api.helpers.connection import queryset_to_connection
from graphql_api.types.enums import OrderingDirection
from graphql_api.types.enums.enums import PullRequestState
from services.comparison import PullRequestComparison

pull_bindable = ObjectType("Pull")

pull_bindable.set_alias("pullId", "pullid")


@pull_bindable.field("state")
def resolve_state(pull, info):
    return PullRequestState(pull.state)


@pull_bindable.field("author")
def resolve_author(pull, info):
    if pull.author_id:
        return OwnerLoader.loader(info).load(pull.author_id)


@pull_bindable.field("head")
def resolve_head(pull, info):
    if pull.head == None:
        return None
    return CommitLoader.loader(info, pull.repository_id).load(pull.head)


@pull_bindable.field("comparedTo")
def resolve_base(pull, info):
    if pull.compared_to == None:
        return None
    return CommitLoader.loader(info, pull.repository_id).load(pull.compared_to)


@pull_bindable.field("compareWithBase")
async def resolve_compare_with_base(pull, info, **kwargs):
    if not pull.compared_to or not pull.head:
        return None

    comparison_loader = ComparisonLoader.loader(info, pull.repository_id)
    commit_comparison = await comparison_loader.load((pull.compared_to, pull.head))

    if commit_comparison and commit_comparison.is_processed:
        user = info.context["request"].user
        comparison = PullRequestComparison(user, pull)
        await sync_to_async(comparison.validate)()

        # store the comparison in the context - to be used in the `Comparison` resolvers
        info.context["comparison"] = comparison

    return commit_comparison


@pull_bindable.field("commits")
async def resolve_commits(pull, info, **kwargs):
    command = info.context["executor"].get_command("commit")
    queryset = await command.fetch_commits_by_pullid(pull)

    return await queryset_to_connection(
        queryset,
        ordering=("timestamp",),
        ordering_direction=OrderingDirection.DESC,
        **kwargs,
    )
