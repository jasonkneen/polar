'use client'

import { FileObject, useFileUpload } from '@/components/FileUpload'
import { FileRead } from '@/components/FileUpload/Upload'
import { useFiles } from '@/hooks/queries'
import { FileUploadOutlined as FileUploadIcon } from '@mui/icons-material'
import { schemas } from '@polar-sh/client'
import { ReactElement, useState } from 'react'
import { useFormContext } from 'react-hook-form'
import { twMerge } from 'tailwind-merge'
import { FileList } from './FileList'

const DropzoneView = ({
  isDragActive,
  children,
}: {
  isDragActive: boolean
  children: ReactElement
}) => {
  return (
    <>
      <div
        className={twMerge(
          'rounded-4xl flex w-full cursor-pointer items-center justify-center border border-transparent pb-8 pt-8',
          isDragActive
            ? 'dark:border-polar-700 dark:bg-polar-950 border-blue-100 bg-blue-50'
            : 'dark:bg-polar-700 bg-gray-100',
        )}
      >
        <div className="dark:text-polar-500 text-center text-gray-700">
          <div className="mb-4">
            <FileUploadIcon fontSize="large" />
          </div>
          <h3 className="font-medium">
            {!isDragActive && 'Feed me some bytes'}
            {isDragActive && "Drop it like it's hot"}
          </h3>
          <p className="mt-2 text-sm">
            You can drop files here or{' '}
            <a className="text-blue-400">click like a Netscape user</a>
          </p>
        </div>
        {children}
      </div>
    </>
  )
}

const DownloadablesForm = ({
  organization,
  initialFiles,
  initialArchivedFiles,
}: {
  organization: schemas['Organization']
  initialFiles: FileRead[]
  initialArchivedFiles: { [key: string]: boolean }
}) => {
  const {
    setValue,
    register,
    clearErrors,
    formState: { errors },
  } = useFormContext<schemas['BenefitDownloadablesCreate']>()

  register('properties.files', {
    minLength: 1,
    required: 'Please upload at least one file',
    validate: {
      notUploading: () =>
        files.filter((file) => !file.is_uploaded).length === 0 ||
        'Please wait for all files to finish uploading',
    },
  })

  const [archivedFiles, setArchivedFiles] = useState<{
    [key: string]: boolean
  }>(initialArchivedFiles ?? {})

  const setFormFiles = (formFiles: FileObject[]) => {
    const files = []

    for (const file of formFiles) {
      if (file.is_uploaded) {
        files.push(file.id)
      }
    }

    if (files.length > 0) {
      clearErrors('properties.files')
    }

    setValue('properties.files', files)
  }

  const setArchivedFile = (fileId: string, archived: boolean) => {
    setArchivedFiles((prev) => {
      const updated = { ...prev, [fileId]: archived }
      if (!archived) {
        delete updated[fileId]
      }
      setValue('properties.archived', updated)
      return updated
    })
  }

  const {
    files,
    setFiles,
    updateFile,
    removeFile,
    getRootProps,
    getInputProps,
    isDragActive,
  } = useFileUpload({
    organization: organization,
    service: 'downloadable',
    onFilesUpdated: setFormFiles,
    initialFiles,
  })

  return (
    <>
      <div {...getRootProps()}>
        <DropzoneView isDragActive={isDragActive}>
          <input {...getInputProps()} />
        </DropzoneView>
      </div>
      <FileList
        files={files}
        setFiles={setFiles}
        updateFile={updateFile}
        removeFile={removeFile}
        archivedFiles={archivedFiles}
        setArchivedFile={setArchivedFile}
      />
      {errors.properties?.files && (
        <p className="text-destructive-foreground text-sm">
          {errors.properties.files.message}
        </p>
      )}
    </>
  )
}

interface DownloadablesBenefitFormProps {
  organization: schemas['Organization']
  update?: boolean
}

const DownloadablesEditForm = ({
  organization,
}: DownloadablesBenefitFormProps) => {
  const { getValues } = useFormContext<schemas['BenefitDownloadablesCreate']>()

  const fileIds = getValues('properties.files')
  const archivedFiles = getValues('properties.archived') ?? {}
  const filesQuery = useFiles(organization.id, fileIds)

  const files =
    filesQuery?.data?.items.filter((v): v is FileRead => Boolean(v)) ?? []

  if (filesQuery.isLoading) {
    // TODO: Style me
    return <div>Loading...</div>
  }

  return (
    <DownloadablesForm
      organization={organization}
      initialFiles={files}
      initialArchivedFiles={archivedFiles}
    />
  )
}

export const DownloadablesBenefitForm = ({
  organization,
  update = false,
}: DownloadablesBenefitFormProps) => {
  if (!update) {
    return (
      <DownloadablesForm
        organization={organization}
        initialFiles={[]}
        initialArchivedFiles={{}}
      />
    )
  }

  return <DownloadablesEditForm organization={organization} />
}
