import click

from ape import accounts, chain, project


def main():
    click.echo(f"Running deploy.py on chainid {chain.chain_id} ...")

    deployer_name = click.prompt("Deployer account name", default="")
    deployer = (
        accounts.load(deployer_name)
        if deployer_name != ""
        else accounts.test_accounts[0]
    )
    click.echo(f"Init balance of deployer: {deployer.balance / 1e18} ETH")

    univ3_factory_addr = click.prompt("Uniswap v3 factory address", type=str)
    univ3_obs_cardinality_min = click.prompt(
        "Observation cardinality minimum", type=int
    )
    publish = click.prompt("Publish to Etherscan?", default=False)

    # deploy marginal v1 deployer if not provided
    pool_deployer_address = None
    if click.confirm("Deploy Marginal v1 pool deployer?"):
        click.echo("Deploying Marginal v1 pool deployer ...")
        pool_deployer = project.MarginalV1PoolDeployer.deploy(
            sender=deployer, publish=publish
        )
        pool_deployer_address = pool_deployer.address
        click.echo(f"Deployed Marginal v1 pool deployer to {pool_deployer_address}")
    else:
        pool_deployer_address = click.prompt(
            "Marginal v1 pool deployer address", type=str
        )

    # deploy marginal v1 factory
    click.echo("Deploying Marginal v1 factory ...")
    factory = project.MarginalV1Factory.deploy(
        pool_deployer_address,
        univ3_factory_addr,
        univ3_obs_cardinality_min,
        sender=deployer,
        publish=publish,
    )
    click.echo(f"Deployed Marginal v1 factory to {factory.address}")
