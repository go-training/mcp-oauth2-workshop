FROM golang:1.26.10 AS build
WORKDIR /src
COPY go/go.mod go/go.sum ./
RUN go mod download
COPY go/ ./
RUN CGO_ENABLED=0 go build -trimpath -o /server ./labs/06
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /server /server
ENTRYPOINT ["/server"]
