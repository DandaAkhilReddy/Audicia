// Audicia SOAP Note System - Azure Infrastructure
// Bicep template for enterprise deployment

@description('Environment name (dev, staging, prod)')
param environment string = 'dev'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Application name prefix')
param appName string = 'audicia-soap'

// Variables
var resourceNamePrefix = '${appName}-${environment}'
var tags = {
  Environment: environment
  Application: 'Audicia SOAP Notes'
  Owner: 'Medical IT Team'
  CostCenter: 'Healthcare Technology'
}

// ==================== NETWORKING ====================

resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: '${resourceNamePrefix}-vnet'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: ['10.0.0.0/16']
    }
    subnets: [
      {
        name: 'app-subnet'
        properties: {
          addressPrefix: '10.0.1.0/24'
          serviceEndpoints: [
            {
              service: 'Microsoft.KeyVault'
            }
            {
              service: 'Microsoft.Storage'
            }
            {
              service: 'Microsoft.Sql'
            }
          ]
        }
      }
      {
        name: 'db-subnet'
        properties: {
          addressPrefix: '10.0.2.0/24'
          delegations: [
            {
              name: 'postgres-delegation'
              properties: {
                serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers'
              }
            }
          ]
        }
      }
    ]
  }
}

// ==================== STORAGE ====================

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: replace('${resourceNamePrefix}storage', '-', '')
  location: location
  tags: tags
  sku: {
    name: 'Standard_GRS'
  }
  kind: 'StorageV2'
  properties: {
    defaultToOAuthAuthentication: true
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    encryption: {
      services: {
        blob: {
          keyType: 'Account'
          enabled: true
        }
        file: {
          keyType: 'Account'
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
    networkAcls: {
      defaultAction: 'Deny'
      virtualNetworkRules: [
        {
          id: vnet.properties.subnets[0].id
          action: 'Allow'
        }
      ]
    }
  }
}

resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    containerDeleteRetentionPolicy: {
      enabled: true
      days: 30
    }
    deleteRetentionPolicy: {
      enabled: true
      days: 30
    }
  }
}

resource soapNotesContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobServices
  name: 'soap-notes'
  properties: {
    publicAccess: 'None'
    metadata: {
      purpose: 'SOAP note document storage'
    }
  }
}

// ==================== DATABASE ====================

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: '${resourceNamePrefix}-postgres'
  location: location
  tags: tags
  sku: {
    name: 'Standard_D2ds_v4'
    tier: 'GeneralPurpose'
  }
  properties: {
    administratorLogin: 'audicia_admin'
    administratorLoginPassword: 'ComplexPassword123!' // Use Key Vault in production
    version: '15'
    storage: {
      storageSizeGB: 128
      autoGrow: 'Enabled'
    }
    backup: {
      backupRetentionDays: 35
      geoRedundantBackup: 'Enabled'
    }
    network: {
      delegatedSubnetResourceId: vnet.properties.subnets[1].id
      privateDnsZoneArmResourceId: postgresPrivateDnsZone.id
    }
    highAvailability: {
      mode: 'ZoneRedundant'
    }
  }
}

resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  parent: postgresServer
  name: 'audicia_soap'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

resource postgresPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'private.postgres.database.azure.com'
  location: 'global'
  tags: tags
}

resource postgresPrivateDnsZoneVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: postgresPrivateDnsZone
  name: 'postgres-vnet-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

// ==================== CACHE ====================

resource redisCache 'Microsoft.Cache/Redis@2023-08-01' = {
  name: '${resourceNamePrefix}-redis'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'Premium'
      family: 'P'
      capacity: 1
    }
    redisConfiguration: {
      'maxmemory-reserved': '30'
      'maxfragmentationmemory-reserved': '30'
      'maxmemory-delta': '30'
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Disabled'
    redisVersion: '6'
  }
}

// ==================== KEY VAULT ====================

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${resourceNamePrefix}-kv'
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'premium'
    }
    tenantId: subscription().tenantId
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: true
    enablePurgeProtection: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    networkAcls: {
      defaultAction: 'Deny'
      virtualNetworkRules: [
        {
          id: vnet.properties.subnets[0].id
          ignoreMissingVnetServiceEndpoint: false
        }
      ]
    }
    accessPolicies: []
  }
}

// ==================== APPLICATION INSIGHTS ====================

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${resourceNamePrefix}-logs'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 90
    features: {
      searchVersion: 1
    }
  }
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${resourceNamePrefix}-insights'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// ==================== CONTAINER REGISTRY ====================

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: replace('${resourceNamePrefix}acr', '-', '')
  location: location
  tags: tags
  sku: {
    name: 'Premium'
  }
  properties: {
    adminUserEnabled: false
    networkRuleSet: {
      defaultAction: 'Deny'
      virtualNetworkRules: [
        {
          action: 'Allow'
          id: vnet.properties.subnets[0].id
        }
      ]
    }
    encryption: {
      status: 'enabled'
    }
    trustPolicy: {
      status: 'enabled'
      type: 'Notary'
    }
    retentionPolicy: {
      status: 'enabled'
      days: 30
    }
  }
}

// ==================== KUBERNETES SERVICE ====================

resource aksCluster 'Microsoft.ContainerService/managedClusters@2023-08-02-preview' = {
  name: '${resourceNamePrefix}-aks'
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    kubernetesVersion: '1.28.0'
    dnsPrefix: '${resourceNamePrefix}-dns'
    agentPoolProfiles: [
      {
        name: 'system'
        count: 3
        vmSize: 'Standard_D4s_v3'
        osType: 'Linux'
        mode: 'System'
        vnetSubnetID: vnet.properties.subnets[0].id
        maxPods: 50
        enableAutoScaling: true
        minCount: 2
        maxCount: 10
      }
      {
        name: 'apps'
        count: 3
        vmSize: 'Standard_D8s_v3'
        osType: 'Linux'
        mode: 'User'
        vnetSubnetID: vnet.properties.subnets[0].id
        maxPods: 50
        enableAutoScaling: true
        minCount: 2
        maxCount: 20
        nodeLabels: {
          workload: 'applications'
        }
      }
    ]
    networkProfile: {
      networkPlugin: 'azure'
      networkPolicy: 'calico'
      serviceCidr: '10.2.0.0/16'
      dnsServiceIP: '10.2.0.10'
      dockerBridgeCidr: '172.17.0.1/16'
    }
    autoUpgradeProfile: {
      upgradeChannel: 'patch'
    }
    addonProfiles: {
      azureKeyvaultSecretsProvider: {
        enabled: true
      }
      azurepolicy: {
        enabled: true
      }
      omsagent: {
        enabled: true
        config: {
          logAnalyticsWorkspaceResourceID: logAnalyticsWorkspace.id
        }
      }
    }
    securityProfile: {
      workloadIdentity: {
        enabled: true
      }
    }
  }
}

// Grant AKS access to ACR
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: containerRegistry
  name: guid(containerRegistry.id, aksCluster.id, 'AcrPull')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: aksCluster.properties.identityProfile.kubeletidentity.objectId
    principalType: 'ServicePrincipal'
  }
}

// ==================== API MANAGEMENT ====================

resource apiManagement 'Microsoft.ApiManagement/service@2023-05-01-preview' = {
  name: '${resourceNamePrefix}-apim'
  location: location
  tags: tags
  sku: {
    name: 'Developer'
    capacity: 1
  }
  properties: {
    publisherName: 'Audicia Medical Systems'
    publisherEmail: 'admin@audicia.com'
    customProperties: {
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Protocols.Server.Http2': 'true'
    }
    virtualNetworkConfiguration: {
      subnetResourceId: vnet.properties.subnets[0].id
    }
    virtualNetworkType: 'Internal'
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ==================== OUTPUTS ====================

output storageAccountName string = storageAccount.name
output postgresServerFqdn string = postgresServer.properties.fullyQualifiedDomainName
output redisCacheHostName string = redisCache.properties.hostName
output keyVaultUri string = keyVault.properties.vaultUri
output aksClusterName string = aksCluster.name
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString
output apiManagementGatewayUrl string = apiManagement.properties.gatewayUrl