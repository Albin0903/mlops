import os
import subprocess
import sys
import argparse
from pathlib import Path

# regle d'ingenierie : commentaires en minuscules pour les instructions techniques
# standards d'ingenierie strictement respectes

class InfraManager:
    def __init__(self, workspace_root: Path):
        self.root = workspace_root
        self.tf_dir = workspace_root / "terraform"
        self.k8s_dir = workspace_root / "k8s"

    def run_command(self, cmd: list, cwd: Path = None):
        """aide pour executer des commandes shell en toute securite"""
        try:
            print(f"--- execution: {' '.join(cmd)} ---")
            subprocess.run(cmd, cwd=cwd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"erreur lors de l'execution de la commande: {e}")
            sys.exit(1)

    def terraform_apply(self, auto_approve: bool = False):
        """initialiser et appliquer la configuration terraform"""
        self.run_command(["terraform", "init"], cwd=self.tf_dir)
        args = ["terraform", "apply"]
        if auto_approve:
            args.append("-auto-approve")
        self.run_command(args, cwd=self.tf_dir)

    def terraform_destroy(self, auto_approve: bool = False):
        """detruire l'infrastructure terraform (securite finops)"""
        args = ["terraform", "destroy"]
        if auto_approve:
            args.append("-auto-approve")
        self.run_command(args, cwd=self.tf_dir)

    def minikube_start(self):
        """demarrer l'environnement kubernetes local"""
        self.run_command(["minikube", "start", "--driver=docker"])
        self.run_command(["minikube", "addons", "enable", "ingress"])

    def deploy_k8s(self):
        """deployer tous les manifestes du dossier k8s"""
        for manifest in self.k8s_dir.glob("*.yaml"):
            self.run_command(["kubectl", "apply", "-f", str(manifest)])

def main():
    parser = argparse.ArgumentParser(description="outil d'automatisation infra (pont dev/ops)")
    parser.add_argument("action", choices=["up", "down", "deploy", "start-local"])
    parser.add_argument("--yes", action="store_true", help="auto-approbation des actions")
    
    args = parser.parse_args()
    manager = InfraManager(Path(__file__).parent.parent)

    if args.action == "up":
        manager.terraform_apply(args.yes)
    elif args.action == "down":
        manager.terraform_destroy(args.yes)
    elif args.action == "start-local":
        manager.minikube_start()
    elif args.action == "deploy":
        manager.deploy_k8s()

if __name__ == "__main__":
    main()
