from agent_squad.orchestrator import AgentSquad
from agent_squad.agents import SupervisorAgent, SupervisorAgentOptions, BedrockLLMAgent, BedrockLLMAgentOptions

class SevaSupervisionSystem:
    def __init__(self):
        self.main_orchestrator = AgentSquad()
        self._setup_supervisor_teams()
    
    def _setup_supervisor_teams(self):
        """Setup supervisor agents with specialized teams"""
        
        # AWS Infrastructure Team
        infrastructure_team = self._create_infrastructure_team()
        infrastructure_supervisor = SupervisorAgent(SupervisorAgentOptions(
            name="InfrastructureSupervisor",
            description="""Coordinates AWS infrastructure operations across multiple services.
            Manages complex workflows involving EC2, VPC, Load Balancers, and networking.
            Specializes in multi-step infrastructure deployments and orchestration.""",
            agents=infrastructure_team
        ))
        
        # DevOps & Deployment Team  
        devops_team = self._create_devops_team()
        devops_supervisor = SupervisorAgent(SupervisorAgentOptions(
            name="DevOpsSupervisor", 
            description="""Orchestrates DevOps workflows and application deployments.
            Coordinates Lambda functions, CI/CD pipelines, and serverless architectures.
            Manages complex deployment scenarios and automation workflows.""",
            agents=devops_team
        ))
        
        # Security & Compliance Team
        security_team = self._create_security_team()
        security_supervisor = SupervisorAgent(SupervisorAgentOptions(
            name="SecuritySupervisor",
            description="""Manages security, compliance, and access control workflows.
            Coordinates IAM policies, security groups, and compliance audits.
            Specializes in multi-service security configurations.""",
            agents=security_team
        ))
        
        # Add supervisors to main orchestrator
        self.main_orchestrator.add_agent(infrastructure_supervisor)
        self.main_orchestrator.add_agent(devops_supervisor)
        self.main_orchestrator.add_agent(security_supervisor)
    
    def _create_infrastructure_team(self):
        """Create infrastructure specialist team"""
        return [
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="EC2Specialist",
                description="Expert in EC2 instances, autoscaling, and compute optimization",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            )),
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="NetworkingSpecialist", 
                description="Expert in VPC, subnets, security groups, and load balancers",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            )),
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="StorageSpecialist",
                description="Expert in S3, EBS, EFS, and data management solutions",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            ))
        ]
    
    def _create_devops_team(self):
        """Create DevOps specialist team"""
        return [
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="ServerlessSpecialist",
                description="Expert in Lambda, API Gateway, and serverless architectures",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            )),
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="ContainerSpecialist",
                description="Expert in ECS, EKS, Docker, and container orchestration", 
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            )),
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="PipelineSpecialist",
                description="Expert in CodePipeline, CodeBuild, and CI/CD automation",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            ))
        ]
    
    def _create_security_team(self):
        """Create security specialist team"""  
        return [
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="IAMSpecialist",
                description="Expert in IAM policies, roles, and access management",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            )),
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="ComplianceSpecialist",
                description="Expert in AWS Config, CloudTrail, and compliance frameworks",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            )),
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="SecuritySpecialist", 
                description="Expert in security groups, NACLs, and threat detection",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            ))
        ]
    
    async def process_complex_request(self, user_query: str, user_id: str = "default", session_id: str = "default"):
        """Process complex multi-service requests through supervisor orchestration"""
        return await self.main_orchestrator.route_request(user_query, user_id, session_id)

# Global supervisor system
seva_supervision = SevaSupervisionSystem()