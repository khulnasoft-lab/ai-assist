{{/*
Expand the name of the chart.
*/}}
{{- define "ai-assist.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "ai-assist.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "ai-assist.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ai-assist.labels" -}}
helm.sh/chart: {{ include "ai-assist.chart" . }}
{{ include "ai-assist.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{ include "common.tplvalues.render" (dict "value" .Values.commonLabels "context" $) }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ai-assist.selectorLabels" -}}
{{/* These are currently commented out because we can't apply selector labels without
downtime. Still deciding if we need them in https://gitlab.com/gitlab-com/gl-infra/reliability/-/issues/23724#note_1413210936
# app.kubernetes.io/name: {{ include "ai-assist.name" . }}
# app.kubernetes.io/instance: {{ .Release.Name }}
*/}}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ai-assist.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "ai-assist.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Renders a value that contains template.
Usage:
{{ include "common.tplvalues.render" ( dict "value" .Values.path.to.the.Value "context" $) }}
*/}}
{{- define "common.tplvalues.render" -}}
    {{- if typeIs "string" .value }}
        {{- tpl .value .context }}
    {{- else }}
        {{- tpl (.value | toYaml) .context }}
    {{- end }}
{{- end -}}
